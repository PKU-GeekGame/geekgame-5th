import asyncio
import logging
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json
from datetime import datetime
import random
import math
import gc
# import objgraph
# import guppy

# analyzer = guppy.hpy()

# Configure logging
logger = logging.getLogger(__name__)

@dataclass(slots=True)
class Order:
    participant_id: str
    price: float
    quantity: int  # positive for buy, negative for sell
    order_type: str  # "buy" or "sell"
    order_id: Optional[str] = None
    time_in_force: str = "GTC"
    
    def __post_init__(self):
        if self.quantity > 0:
            self.order_type = "buy"
        else:
            self.order_type = "sell"

        if self.time_in_force:
            self.time_in_force = self.time_in_force.upper()


@dataclass(slots=True)
class Trade:
    buyer_id: str
    seller_id: str
    price: float
    quantity: int
    taker: int  # 1 if buyer is taker, -1 if seller is taker
    tick: int  # tick number


@dataclass
class OrderBookSnapshot:
    tick: int
    buy_orders: List[Order]
    sell_orders: List[Order]
    trades: List[Trade]
    last_price: float


class Participant(ABC):
    def __init__(self, exchange, participant_id: str):
        self.exchange = exchange
        self.participant_id = participant_id
    
    @abstractmethod
    def get_orders(self, current_price: float, tick: int) -> List[Order]:
        pass
    
    @abstractmethod
    def on_trade(self, trade: Trade, side: str):
        pass

    @abstractmethod
    def on_news(self, rating: float):
        pass


class Exchange:
    def __init__(self, tick_duration: float = 0.1):
        self.tick_duration = tick_duration
        self.participants: List[Participant] = []
        self.price_history: List[float] = []
        self.order_book_history: List[OrderBookSnapshot] = []
        self.current_tick = 0
        self.last_price = 100.0  # Initial price
        self.news_prob = 0.01  # Probability of news each tick
        self.current_orders: List[Order] = []
        self.current_trades: List[Trade] = []
        self.websocket_clients = set()
        self.tick_messages = []
        self.user_order_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None
        
    def add_participant(self, participant: Participant):
        self.participants.append(participant)
        logger.info(f"Added participant: {participant.participant_id}")

    def set_user_order_provider(self, provider: Optional[Callable[[], List[Dict[str, Any]]]]):
        self.user_order_provider = provider
        
    def get_current_price(self) -> float:
        return self.last_price if self.price_history else 100.0
        
    def get_price_history(self) -> List[float]:
        return self.price_history.copy()
        
    def get_order_book_history(self) -> List[OrderBookSnapshot]:
        return self.order_book_history.copy()
    
    def send_news(self, rating: float):
        """Broadcast news sentiment to all participants"""
        logger.info(f"Broadcasting news with rating: {rating}")
        for participant in self.participants:
            if hasattr(participant, 'on_news'):
                participant.on_news(rating)
        
    async def run_simulation(self, total_ticks: int = 9000):
        logger.info(f"Starting simulation for {total_ticks} ticks")
        
        for tick in range(1, total_ticks+1):
            self.current_tick = tick
            self.current_orders = []
            self.current_trades = []

            if random.random() < self.news_prob:
                rating = random.uniform(-0.05, 0.05)
                power = math.exp(random.uniform(0, 10)) / math.exp(10)
                self.send_news(rating * power)
                logger.info(f"Tick {tick}: News event with rating {rating * power:.4f}")

            # Collect orders from all participants
            current_price = self.get_current_price()
            logger.debug(f"Tick {tick}: Current price ${current_price:.2f}")
            
            order_count = 0
            for participant in self.participants:
                orders = participant.get_orders(current_price, tick)
                self.current_orders.extend(orders)
                order_count += len(orders)
                
                # Log orders from each participant
                if orders:
                    logger.info(f"Tick {tick} - {participant.participant_id}: Placed {len(orders)} orders")
                    orders = sorted(orders, key=lambda x: (x.price, x.participant_id))
                    for order in orders:
                        logger.info(f"  {'BUY' if order.quantity > 0 else 'SELL'} {abs(order.quantity)} @ ${order.price:.2f}")
            
            logger.info(f"Tick {tick}: Total {order_count} orders collected ({len([o for o in self.current_orders if o.order_type == 'buy'])} buy, {len([o for o in self.current_orders if o.order_type == 'sell'])} sell)")
            
            # Match orders
            await self._match_orders()
            
            # Update price history
            if self.current_trades:
                # Use average price of trades in this tick
                avg_price = sum(trade.price for trade in self.current_trades) / len(self.current_trades)
                self.last_price = avg_price
                logger.info(f"Tick {tick}: {len(self.current_trades)} trades executed, new price ${self.last_price:.2f}")
            else:
                logger.info(f"Tick {tick}: No trades executed, price remains ${self.last_price:.2f}")
            
            self.price_history.append(self.last_price)
            
            # Create order book snapshot
            snapshot = OrderBookSnapshot(
                tick=tick,
                buy_orders=[o for o in self.current_orders if o.order_type == "buy"],
                sell_orders=[o for o in self.current_orders if o.order_type == "sell"],
                trades=self.current_trades.copy(),
                last_price=self.last_price
            )
            self.order_book_history.append(snapshot)
            if len(self.order_book_history) > 100:
                self.order_book_history.pop(0)
            
            # Notify participants of trades
            for trade in self.current_trades:
                logger.debug(f"Tick {tick}: Notifying participants of trade - {trade.quantity} @ ${trade.price:.2f}")
                for participant in self.participants:
                    flag = False
                    if participant.participant_id == trade.buyer_id:
                        participant.on_trade(trade, side='buy')
                        flag = True
                    if participant.participant_id == trade.seller_id:
                        participant.on_trade(trade, side='sell')
                        flag = True
                    if not flag:
                        participant.on_trade(trade, side='none')
                    
            
            # Broadcast to WebSocket clients
            await self._broadcast_update(snapshot)

            if tick % 100 == 0:
                gc.collect()
                # objgraph.show_most_common_types(limit=50)  
                # heap = analyzer.heap()
                # print(heap)
                # print(heap.bytype)
                # print(heap.byid[0].sp)
                # references = heap[0].byvia
                # print(references)
                # print("==={} references detail===")
                # print(references[0].kind)  # 类型
                # print(references[0].shpaths)  # 路径
                # print(references[0].rp)  # 引用
                # logger.info(f"Tick {tick}: Performed garbage collection")
            
            # Small delay to simulate real-time
            await asyncio.sleep(self.tick_duration)
    
    async def _match_orders(self):
        logger.info(f"Tick {self.current_tick}: Processing {len(self.current_orders)} incoming orders")

        resting_buys: List[Order] = []
        resting_sells: List[Order] = []
        executed_trades: List[Trade] = []

        def log_book_state():
            if resting_buys:
                best_buy = max(resting_buys, key=lambda o: o.price)
                logger.debug(f"Tick {self.current_tick}: Best bid {best_buy.quantity} @ ${best_buy.price:.2f}")
            if resting_sells:
                best_sell = min(resting_sells, key=lambda o: o.price)
                logger.debug(f"Tick {self.current_tick}: Best ask {abs(best_sell.quantity)} @ ${best_sell.price:.2f}")

        for incoming in self.current_orders:
            is_buy = incoming.quantity > 0
            remaining_qty = abs(incoming.quantity)

            resting_side = resting_sells if is_buy else resting_buys
            opposing_label = "asks" if is_buy else "bids"

            if is_buy:
                resting_side.sort(key=lambda o: (o.price, o.participant_id))
            else:
                resting_side.sort(key=lambda o: (-o.price, o.participant_id))

            logger.debug(
                f"Tick {self.current_tick}: Handling incoming {'BUY' if is_buy else 'SELL'} order "
                f"{abs(incoming.quantity)} @ ${incoming.price:.2f} from {incoming.participant_id}"
            )

            idx = 0
            while remaining_qty > 0 and idx < len(resting_side):
                resting_order = resting_side[idx]
                price_match = (
                    incoming.price >= resting_order.price if is_buy
                    else incoming.price <= resting_order.price
                )

                if not price_match:
                    break

                trade_qty = min(remaining_qty, abs(resting_order.quantity))
                trade_price = resting_order.price

                taker_flag = 1 if is_buy else -1

                trade = Trade(
                    buyer_id=incoming.participant_id if is_buy else resting_order.participant_id,
                    seller_id=resting_order.participant_id if is_buy else incoming.participant_id,
                    price=trade_price,
                    quantity=trade_qty,
                    taker=taker_flag,
                    tick=self.current_tick
                )
                executed_trades.append(trade)
                logger.info(
                    f"Tick {self.current_tick}: Trade {trade_qty} @ ${trade_price:.2f} "
                    f"(buyer={trade.buyer_id}, seller={trade.seller_id}, taker={'buyer' if taker_flag==1 else 'seller'})"
                )

                remaining_qty -= trade_qty
                if resting_order.quantity > 0:
                    resting_order.quantity -= trade_qty
                else:
                    resting_order.quantity += trade_qty

                if resting_order.quantity == 0:
                    resting_side.pop(idx)
                else:
                    idx += 1

            if remaining_qty > 0:
                incoming.quantity = remaining_qty if is_buy else -remaining_qty
                if incoming.time_in_force != "IOC":
                    if is_buy:
                        resting_buys.append(incoming)
                    else:
                        resting_sells.append(incoming)
                    logger.debug(
                        f"Tick {self.current_tick}: Order partially/fully resting with {remaining_qty} remaining"
                    )
                else:
                    logger.debug(
                        f"Tick {self.current_tick}: IOC order {incoming.order_id or incoming.participant_id} expired with {remaining_qty} unfilled"
                    )
            else:
                incoming.quantity = 0

            log_book_state()

        self.current_trades = executed_trades

        resting_buys.sort(key=lambda o: (-o.price, o.participant_id))
        resting_sells.sort(key=lambda o: (o.price, o.participant_id))
        self.current_orders = resting_buys + resting_sells

        logger.info(
            f"Tick {self.current_tick}: Matching complete - {len(executed_trades)} trades executed, "
            f"book depth {len(resting_buys)} bids / {len(resting_sells)} asks"
        )

    async def _broadcast_update(self, snapshot: OrderBookSnapshot):
        # Calculate mid price
        best_buy_price = max([order.price for order in snapshot.buy_orders], default=0) if snapshot.buy_orders else 0
        best_sell_price = min([order.price for order in snapshot.sell_orders], default=0) if snapshot.sell_orders else 0
        
        mid_price = 0
        if best_buy_price > 0 and best_sell_price > 0:
            mid_price = (best_buy_price + best_sell_price) / 2
        elif best_buy_price > 0:
            mid_price = best_buy_price
        elif best_sell_price > 0:
            mid_price = best_sell_price
        
        # Sanitize orders and trades by removing participant IDs
        sanitized_buy_orders = []
        for order in snapshot.buy_orders:
            sanitized_buy_orders.append({
                'price': order.price,
                'quantity': order.quantity
            })
        
        sanitized_sell_orders = []
        for order in snapshot.sell_orders:
            sanitized_sell_orders.append({
                'price': order.price,
                'quantity': abs(order.quantity)
            })
        
        sanitized_trades = []
        for trade in snapshot.trades:
            sanitized_trades.append({
                'price': trade.price,
                'quantity': trade.quantity,
                'taker': trade.taker
            })
        
        message = {
            'type': 'tick_update',
            'tick': snapshot.tick,
            'last_price': snapshot.last_price,
            'mid_price': mid_price,
            'best_buy_price': best_buy_price,
            'best_sell_price': best_sell_price,
            'order_book': {
                'buy_orders': sanitized_buy_orders,
                'sell_orders': sanitized_sell_orders
            },
            'trades': sanitized_trades,
            'trade_summary': {
                'trade_count': len(snapshot.trades),
                'total_volume': sum(trade.quantity for trade in snapshot.trades),
                'avg_trade_price': sum(trade.price for trade in snapshot.trades) / len(snapshot.trades) if snapshot.trades else 0
            },
            'user_orders': []
        }

        if self.user_order_provider:
            try:
                user_orders = self.user_order_provider()
                message['user_orders'] = user_orders
            except Exception as exc:
                logger.error(f"Failed to retrieve user order snapshot: {exc}")
            
        self.tick_messages.append(json.dumps(message))
        if len(self.tick_messages) > 100:
            self.tick_messages.pop(0)
            # logger.debug(f"Tick {snapshot.tick}: Broadcasting update to {len(self.websocket_clients)} WebSocket clients")
            
            # Send to all connected clients (iterate over snapshot to avoid concurrent mutation)
        if self.websocket_clients:
            disconnected = set()
            clients_snapshot = list(self.websocket_clients)
            for client in clients_snapshot:
                try:
                    await client.send(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket client: {e}")
                    disconnected.add(client)
            
            # Remove disconnected clients
            if disconnected:
                logger.info(f"Removed {len(disconnected)} disconnected WebSocket clients")
            self.websocket_clients -= disconnected

    def add_websocket_client(self, client):
        self.websocket_clients.add(client)
        if len(self.tick_messages) > 0:
            asyncio.create_task(client.send(self.tick_messages[-1]))
        logger.info(f"Added WebSocket client. Total clients: {len(self.websocket_clients)}")
        
    def remove_websocket_client(self, client):
        self.websocket_clients.discard(client)
        logger.info(f"Removed WebSocket client. Total clients: {len(self.websocket_clients)}")
        
    async def send_historical_data(self, client):
        logger.info(f"Sending historical data to WebSocket client")
        historical_data = {
            'type': 'historical_data',
            'price_history': self.price_history,
            'order_book_history': [
                {
                    'tick': s.tick,
                    'last_price': s.last_price,
                    'buy_orders': [{'price': o.price, 'quantity': o.quantity} for o in s.buy_orders],
                    'sell_orders': [{'price': o.price, 'quantity': abs(o.quantity)} for o in s.sell_orders],
                    'trades': [{'price': t.price, 'quantity': t.quantity, 'buyer': t.buyer_id, 'seller': t.seller_id} for t in s.trades]
                }
                for s in self.order_book_history
            ]
        }
        try:
            await client.send(json.dumps(historical_data))
            logger.info(f"Historical data sent successfully")
        except Exception as e:
            logger.error(f"Failed to send historical data to WebSocket client: {e}")
            raise