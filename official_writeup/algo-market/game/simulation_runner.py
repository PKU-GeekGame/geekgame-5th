import asyncio
import argparse
import logging
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Dict, Any
from aiohttp import web, WSMsgType
from exchange import Exchange
from amm_market_maker import AMMMarketMaker
from as_market_maker import ASMarketMaker
from retail_trader import RetailTrader
from user_trader import UserTrader
import math
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AiohttpWebSocketClient:
    def __init__(self, websocket: web.WebSocketResponse, client_id: str):
        self.websocket = websocket
        self.client_id = client_id

    async def send(self, message: str):
        await self.websocket.send_str(message)

    async def close(self, message: Optional[str] = None):
        await self.websocket.close(message=message or "")


class SimulationRunner:
    def __init__(self, config: dict):
        self.config = config
        self.exchange = Exchange(tick_duration=config.get('tick_duration', 0.1))
        self.results: Dict[str, Any] = {}
        self.last_error: Optional[str] = None
        self.simulation_task: Optional[asyncio.Task] = None
        self.simulation_lock = asyncio.Lock()
        self.websocket_clients: Set[AiohttpWebSocketClient] = set()
        self.client_counter = 0
        self.frontend_path = Path(__file__).with_name('frontend.html')
        self.started = False
        self.truth_count = 0
        self.truth_total = 10
        self.user_trader: Optional[UserTrader] = None

        self.app = web.Application()
        self.app.add_routes([
            web.get('/', self.handle_frontend),
            web.post('/simulation/start', self.handle_start_simulation),
            web.post('/simulation/kill', self.handle_kill_simulation),
            web.post('/simulation/tick-duration', self.handle_tick_duration),
            web.post('/simulation/send-truth', self.handle_send_truth),
            web.get('/simulation/status', self.handle_status),
            web.get('/ws', self.handle_websocket),
            # User trading APIs
            web.post('/user/orders', self.handle_create_user_order),
            web.post('/user/orders/{order_id}/cancel', self.handle_cancel_user_order),
            web.get('/user/orders', self.handle_list_user_orders),
            web.get('/user/getflag', self.handle_get_flag),
        ])

    def read_flag(self, flagid):
        assert flagid in [1, 2, 3]
        filename = f'/flag{flagid}'
        if not os.path.exists(filename):
            return "info{flag_not_found_contact_admin}"
        with open(filename, 'r') as f:
            return f.read().strip()

    def setup_participants(self, num_retail=50):
        logger.info("Setting up market participants...")

        amm = AMMMarketMaker(
            exchange=self.exchange,
            participant_id=f"AMM_1",
            initial_cash=5000000,
            initial_stock=50000
        )
        self.exchange.add_participant(amm)
        logger.info(f"Added AMM market maker: {amm.participant_id}")

        asmm = ASMarketMaker(
            exchange=self.exchange,
            participant_id=f"ASM_2"
        )
        self.exchange.add_participant(asmm)
        logger.info(f"Added AS market maker: {asmm.participant_id}")

        self.user_trader = UserTrader(
            exchange=self.exchange,
            participant_id="User",
            initial_cash=5000000,
            initial_stock=0
        )
        self.exchange.add_participant(self.user_trader)
        self.exchange.set_user_order_provider(self.user_trader.get_user_info)
        logger.info(f"Added API user trader: {self.user_trader.participant_id}")

        for i in range(num_retail):
            config = {
                'base_trade_prob': random.uniform(0.02, 0.2),
                'price_sensitivity': random.uniform(2.0, 10.0),
                'position_sensitivity': random.uniform(0.2, 1.0),
                'direction_price_weight': random.uniform(0.5, 2.0),
                'direction_position_weight': random.uniform(0.05, 0.2),
                'direction_noise': random.uniform(0.1, 0.3),
                'size_price_weight': random.uniform(0.6, 1.0),
                'size_position_weight': random.uniform(0.1, 0.3),
                'min_size_fraction': random.uniform(0.05, 0.2),
                'target_stock_ratio': random.uniform(0.8, 0.99),
                'adaptation_rate': random.uniform(0.01, 0.06),
                'news_sensitivity': random.uniform(0.7, 1.3),
                'max_order_size': random.randint(200, 1000),
                'slippage_pct': random.uniform(0.01, 0.03)
            }
            retail_trader = RetailTrader(
                exchange=self.exchange,
                participant_id=f"Retail_{i+1}",
                initial_cash=random.uniform(10000, 100000),
                initial_stock=random.randint(500, 5000),
                behavior_config = config
            )
            self.exchange.add_participant(retail_trader)
            logger.info(f"Added retail trader: {retail_trader.participant_id}")

    async def send_status(self, client: AiohttpWebSocketClient):
        """Send current simulation status to a WebSocket client"""
        running = self.simulation_task is not None and not self.simulation_task.done()
        completed = bool(self.results)

        status = 'running' if running else 'idle'
        if not running and completed:
            status = 'completed'
        if self.last_error and not running:
            status = 'error'

        message = {
            'type': 'status_update',
            'status': status,
            'current_tick': self.exchange.current_tick,
            'tick_duration': self.exchange.tick_duration,
            'truth_count': self.truth_count,
            'truth_total': self.truth_total
        }

        message_str = json.dumps(message)

        try:
            await client.send(message_str)
        except Exception as e:
            logger.error(f"Failed to send status to client {client.client_id}: {e}")
    
    async def broadcast_status(self):
        """Broadcast current simulation status to all connected WebSocket clients"""
        running = self.simulation_task is not None and not self.simulation_task.done()
        completed = bool(self.results)

        status = 'running' if running else 'idle'
        if not running and completed:
            status = 'completed'
        if self.last_error and not running:
            status = 'error'

        message = {
            'type': 'status_update',
            'status': status,
            'current_tick': self.exchange.current_tick,
            'tick_duration': self.exchange.tick_duration,
            'truth_count': self.truth_count,
            'truth_total': self.truth_total
        }

        print("Broadcasting status update:", message)

        message_str = json.dumps(message)

        for client in list(self.websocket_clients):
            try:
                await client.send(message_str)
            except Exception as e:
                logger.error(f"Failed to send status to client {client.client_id}: {e}")

    async def handle_frontend(self, request: web.Request) -> web.StreamResponse:
        if not self.frontend_path.exists():
            logger.warning(f"Requested frontend not found at {self.frontend_path}")
            return web.Response(status=404, text="frontend.html not found")

        return web.FileResponse(path=self.frontend_path)

    async def handle_start_simulation(self, request: web.Request) -> web.Response:
        payload = await self._get_request_payload(request)

        async with self.simulation_lock:

            if self.simulation_task or self.started:
                return web.json_response({'error': 'already_running'}, status=409)
            self.started = True

            self.setup_participants()

            total_ticks = self.config.get('total_ticks', 9000)

            self.simulation_task = asyncio.create_task(
                self._run_simulation(total_ticks)
            )
            asyncio.create_task(self.broadcast_status())

        return web.json_response({'status': 'started', 'total_ticks': total_ticks})
    
    async def handle_kill_simulation(self, request: web.Request) -> web.Response:
        # exit(0)
        os._exit(0)

    async def handle_send_truth(self, request: web.Request) -> web.Response:
        payload = await self._get_request_payload(request)
        if 'rating' not in payload:
            return web.json_response({'error': 'truth is required'}, status=400)

        if not self.started or not self.simulation_task or self.simulation_task.done():
            return web.json_response({'error': 'simulation not running'}, status=400)
        
        if self.truth_count >= self.truth_total:
            return web.json_response({'error': 'truth limit reached'}, status=400)

        try:
            rating = float(payload['rating'])
            rating = 1.0 if rating > 0 else -1.0
            taco = 0.2*(0.5+0.5*math.exp(-0.2*self.truth_count))
            self.truth_count += 1
            self.exchange.send_news(rating*taco)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=400)
        
        asyncio.create_task(self.broadcast_status())
        
        return web.json_response({'status': 'sent', 'current_count': self.truth_count, 'total_allowed': self.truth_total})

    async def _run_simulation(self, total_ticks: int):
        logger.info("Simulation task started")
        start_time = datetime.now()

        try:
            await self.exchange.run_simulation(total_ticks)

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Simulation completed in {duration:.2f} seconds")
            logger.info(f"Processed {total_ticks} ticks")
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"Simulation failed: {exc}")
        finally:
            self.simulation_task = None

    async def handle_tick_duration(self, request: web.Request) -> web.Response:
        payload = await self._get_request_payload(request)
        if 'tick_duration' not in payload:
            return web.json_response({'error': 'tick_duration is required'}, status=400)

        try:
            tick_duration = float(payload['tick_duration'])
            if tick_duration < 0.01 or tick_duration > 0.5:
                raise ValueError
        except (ValueError, TypeError):
            return web.json_response({'error': 'tick_duration must be between 0.01 and 0.5'}, status=400)

        self.exchange.tick_duration = tick_duration
        self.config['tick_duration'] = tick_duration
        logger.info(f"Tick duration updated to {tick_duration}")

        asyncio.create_task(self.broadcast_status())

        return web.json_response({'status': 'updated', 'tick_duration': tick_duration})

    async def handle_status(self, request: web.Request) -> web.Response:
        running = self.simulation_task is not None and not self.simulation_task.done()
        completed = bool(self.results)

        status = 'running' if running else 'idle'
        if not running and completed:
            status = 'completed'
        if self.last_error and not running:
            status = 'error'

        response = {
            'status': status,
            'current_tick': self.exchange.current_tick,
            'tick_duration': self.exchange.tick_duration,
            'results_available': completed,
            'error': self.last_error
        }

        if completed:
            response['summary'] = self.results.get('simulation_summary', {})

        return web.json_response(response)

    async def handle_websocket(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.client_counter += 1
        client = AiohttpWebSocketClient(ws, f"client_{self.client_counter}")
        self.websocket_clients.add(client)
        self.exchange.add_websocket_client(client)
        logger.info(f"WebSocket client connected: {client.client_id}")

        try:
            # Send historical prices on connection
            await self.send_historical_prices(client)
            await self.send_status(client)
            
            # Keep connection alive and wait for disconnection
            # The exchange will push updates automatically
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Ignore any incoming messages - this is one-way communication
                    logger.debug(f"Received message from {client.client_id}, ignoring: {msg.data}")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket connection error: {ws.exception()}")
                    break
                elif msg.type == WSMsgType.CLOSE:
                    logger.info(f"WebSocket client initiated close: {client.client_id}")
                    break
        except Exception as e:
            logger.error(f"WebSocket error for client {client.client_id}: {e}")
        finally:
            self.websocket_clients.discard(client)
            self.exchange.remove_websocket_client(client)
            logger.info(f"WebSocket client disconnected: {client.client_id}")

        return ws

    
    async def send_historical_prices(self, client: AiohttpWebSocketClient):
        """Send historical price data to WebSocket client on connection"""
        logger.info(f"Sending historical prices to WebSocket client {client.client_id}")
        
        # Send all historical prices
        historical_data = {
            'type': 'historical_prices',
            'price_history': self.exchange.get_price_history(),
            'current_tick': len(self.exchange.order_book_history),
            'total_ticks': self.config.get('total_ticks', 9000)
        }
        
        try:
            await client.send(json.dumps(historical_data))
            logger.info(f"Historical prices sent to client {client.client_id}")
        except Exception as e:
            logger.error(f"Failed to send historical prices to client {client.client_id}: {e}")
            raise

    async def _get_request_payload(self, request: web.Request) -> Dict[str, Any]:
        if request.can_read_body:
            try:
                return await request.json()
            except Exception:
                return {}
        return {}

    def _parse_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 't', 'yes', 'y'}
        if isinstance(value, (int, float)):
            return value != 0
        return False

    async def handle_create_user_order(self, request: web.Request) -> web.Response:
        if not self.user_trader:
            return web.json_response({'error': 'user_trader_unavailable'}, status=503)
        if not self.started or not self.simulation_task or self.simulation_task.done():
            return web.json_response({'error': 'simulation_not_running'}, status=409)

        payload = await self._get_request_payload(request)
        missing = [key for key in ('direction', 'price', 'quantity') if key not in payload]
        if missing:
            return web.json_response({'error': f"missing_fields: {', '.join(missing)}"}, status=400)

        try:
            direction = str(payload['direction']).lower()
            price = float(payload['price'])
            quantity = int(payload['quantity'])
        except (ValueError, TypeError):
            return web.json_response({'error': 'invalid_parameter_types'}, status=400)

        immediate_cancel = self._parse_bool(payload.get('immediate_cancel', False))

        valid_ticks = 9001
        if 'valid_ticks' in payload and payload['valid_ticks'] is not None:
            try:
                valid_ticks = int(payload['valid_ticks'])
            except (TypeError, ValueError):
                return web.json_response({'error': 'valid_ticks must be an integer'}, status=400)
            if valid_ticks <= 0:
                return web.json_response({'error': 'valid_ticks must be positive'}, status=400)

        try:
            order_info = self.user_trader.submit_order(
                direction,
                price,
                quantity,
                immediate_cancel,
                valid_ticks=valid_ticks
            )
        except ValueError as exc:
            return web.json_response({'error': str(exc)}, status=400)

        return web.json_response({
            'status': 'accepted',
            'order': order_info
        })

    async def handle_cancel_user_order(self, request: web.Request) -> web.Response:
        if not self.user_trader:
            return web.json_response({'error': 'user_trader_unavailable'}, status=503)

        order_id = request.match_info.get('order_id')
        if not order_id:
            return web.json_response({'error': 'order_id_required'}, status=400)

        result = self.user_trader.cancel_order(order_id)
        if not result:
            return web.json_response({'error': 'order_not_found_or_closed'}, status=404)

        return web.json_response({
            'status': 'cancelled',
            'order': result
        })

    async def handle_list_user_orders(self, request: web.Request) -> web.Response:
        if not self.user_trader:
            return web.json_response({'error': 'user_trader_unavailable'}, status=503)

        return web.json_response(self.user_trader.get_user_info())
    
    async def handle_get_flag(self, request: web.Request) -> web.Response:
        if not self.user_trader:
            return web.json_response({'error': 'user_trader_unavailable'}, status=503)
        if not self.started:
            return web.json_response({'error': 'simulation_not_running'}, status=409)

        try:
            user_portfolio = self.user_trader.get_user_info()['portfolio']['cash_total']
            if user_portfolio >= 6000000:
                flag1 = self.read_flag(1)
            else:
                flag1 = "info{cash<6m_try_harder}"
            if user_portfolio >= 7500000:
                flag2 = self.read_flag(2)
            else:
                flag2 = "info{cash<7.5m_try_harder}"
            if user_portfolio >= 9000000:
                flag3 = self.read_flag(3)
            else:
                flag3 = "info{cash<9m_try_harder}"
        except Exception as e:
            logger.error(f"Error reading flag: {e}")
            return web.json_response({'error': 'internal_error'}, status=500)

        return web.json_response({
            'status': 'success',
            'flag1': flag1,
            'flag2': flag2,
            'flag3': flag3
        })
    

def main():
    parser = argparse.ArgumentParser(description="Trading Simulation Service")
    parser.add_argument('--http-host', default='0.0.0.0', help='HTTP server host')
    parser.add_argument('--http-port', type=int, default=8080, help='HTTP server port')
    parser.add_argument('--ticks', type=int, default=9000, help='Default total simulation ticks')
    parser.add_argument('--tick-duration', type=float, default=0.1, help='Default duration of each tick in seconds')
    parser.add_argument('--retail', type=int, default=5, help='Default number of retail traders')

    args = parser.parse_args()

    config = {
        'total_ticks': args.ticks,
        'tick_duration': args.tick_duration,
        'num_retail_traders': args.retail,
    }

    runner = SimulationRunner(config)

    logger.info("Starting simulation service with defaults:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")

    web.run_app(runner.app, host=args.http_host, port=args.http_port)


if __name__ == "__main__":
    main()