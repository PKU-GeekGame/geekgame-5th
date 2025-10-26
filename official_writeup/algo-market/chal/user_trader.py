import uuid
from typing import List, Dict, Any, Optional, Tuple
from exchange import Participant, Order, Trade


class UserTrader(Participant):
    """Participant controlled via external API requests."""

    def __init__(self, exchange, participant_id: str = "UserTrader", initial_cash: float = 0.0, initial_stock: int = 0):
        super().__init__(exchange, participant_id)
        self.open_orders: Dict[str, Order] = {}
        self.order_state: Dict[str, Dict[str, Any]] = {}
        self.order_sequence: List[str] = []
        self._ioc_orders: Dict[str, int] = {}
        self.cash_total = initial_cash
        self.stock_total = initial_stock
        self._last_tick = 0
        self._last_finalized_tick = 0

    def get_orders(self, current_price: float, tick: int) -> List[Order]:
        self._expire_ioc_orders(tick)
        active_orders: List[Order] = []

        for order_id in self.order_sequence:
            state = self.order_state.get(order_id)
            if not state or state['status'] != 'open':
                continue
            if self.exchange.current_tick > state['expiry_tick']:
                state['status'] = 'expired'
                self.open_orders.pop(order_id, None)
                self._ioc_orders.pop(order_id, None)
                continue

            order = self.open_orders.get(order_id)
            if order is None:
                continue

            if state['created_tick'] is None:
                state['created_tick'] = tick

            active_orders.append(order)

        self._last_tick = tick
        return active_orders

    def on_trade(self, trade: Trade, side: str):
        if side not in ['buy', 'sell']:
            return

        remaining_fill = trade.quantity

        porder_id = list(self.open_orders.keys())
        if side == 'buy':
            self.stock_total += trade.quantity
            self.cash_total -= trade.price * trade.quantity
            porder_id.sort(key=lambda o: self.open_orders[o].price, reverse=True)
        else:
            self.stock_total -= trade.quantity
            self.cash_total += trade.price * trade.quantity
            porder_id.sort(key=lambda o: self.open_orders[o].price)


        for order_id in porder_id:
            state = self.order_state.get(order_id)
            if not state or state['status'] != 'open' or state['direction'] != side:
                continue

            if remaining_fill <= 0:
                break

            fill_qty = min(state['remaining'], remaining_fill)
            state['remaining'] -= fill_qty
            remaining_fill -= fill_qty

            order = self.open_orders.get(order_id)
            if order:
                if side == 'buy':
                    order.quantity = state['remaining']
                else:
                    order.quantity = -state['remaining']

            if state['remaining'] == 0:
                state['status'] = 'filled'
                self.open_orders.pop(order_id, None)
                self._ioc_orders.pop(order_id, None)

    def on_news(self, rating: float):
        # User trader does not react automatically to news
        return
    
    def get_available(self) -> Tuple[float, int]:
        """Get available cash and stock for new orders"""
        used_cash = sum(
            order.price * order.quantity
            for order in self.open_orders.values()
            if order.quantity > 0
        )
        used_stock = sum(
            -order.quantity
            for order in self.open_orders.values()
            if order.quantity < 0
        )
        available_cash = self.cash_total - used_cash
        available_stock = self.stock_total - used_stock
        return available_cash, available_stock

    def submit_order(self, direction: str, price: float, quantity: int, immediate_cancel: bool, valid_ticks: int) -> Dict[str, Any]:
        direction = direction.lower()
        if direction not in {'buy', 'sell'}:
            raise ValueError('direction must be "buy" or "sell"')
        if price <= 0:
            raise ValueError('price must be positive')
        if quantity <= 0:
            raise ValueError('quantity must be positive')
        
        available_cash, available_stock = self.get_available()
        if direction == 'buy' and (price * quantity > available_cash):
            raise ValueError('insufficient available cash for buy order')
        if direction == 'sell' and (quantity > available_stock):
            raise ValueError('insufficient available stock for sell order')

        order_id = str(uuid.uuid4())
        signed_qty = quantity if direction == 'buy' else -quantity
        tif = 'IOC' if immediate_cancel else 'GTC'

        order = Order(
            participant_id=self.participant_id,
            price=price,
            quantity=signed_qty,
            order_type=direction,
            order_id=order_id,
            time_in_force=tif
        )

        self.open_orders[order_id] = order
        self.order_state[order_id] = {
            'order_id': order_id,
            'direction': direction,
            'price': price,
            'original_quantity': quantity,
            'remaining': quantity,
            'time_in_force': tif,
            'status': 'open',
            'created_tick': None,
            'expiry_tick': self.exchange.current_tick + valid_ticks if valid_ticks > 0 else 9001
        }
        self.order_sequence.append(order_id)

        if tif == 'IOC':
            # Track tick of submission for later expiration
            self._ioc_orders[order_id] = -1

        return self._snapshot_order(order_id)

    def cancel_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        state = self.order_state.get(order_id)
        if not state or state['status'] != 'open':
            return None

        state['status'] = 'cancelled'
        self.open_orders.pop(order_id, None)
        self._ioc_orders.pop(order_id, None)

        return self._snapshot_order(order_id)

    def get_open_orders_snapshot(self) -> List[Dict[str, Any]]:
        self._finalize_ioc_orders()
        snapshot: List[Dict[str, Any]] = []
        for order_id in self.order_sequence:
            state = self.order_state.get(order_id)
            if not state or state['status'] != 'open':
                continue
            snapshot.append(self._snapshot_order(order_id))
        return snapshot

    def get_order_state(self, order_id: str) -> Optional[Dict[str, Any]]:
        self._finalize_ioc_orders()
        if order_id not in self.order_state:
            return None
        return self._snapshot_order(order_id)

    def get_all_orders_snapshot(self) -> List[Dict[str, Any]]:
        self._finalize_ioc_orders()
        return [self._snapshot_order(order_id) for order_id in self.order_sequence][-100:]
    
    def get_user_info(self) -> Dict[str, Any]:
        available_cash, available_stock = self.get_available()
        return {
            'open_orders': self.get_open_orders_snapshot(),
            'all_orders': self.get_all_orders_snapshot(),
            'portfolio': {
                'cash_total': self.cash_total,
                'stock_total': self.stock_total,
                'cash_available': available_cash,
                'stock_available': available_stock
            },
            'current_tick': self.exchange.current_tick
        }

    def _expire_ioc_orders(self, tick: int):
        expired: List[str] = []
        for order_id, created_tick in list(self._ioc_orders.items()):
            state = self.order_state.get(order_id)
            if not state or state['status'] != 'open':
                expired.append(order_id)
                continue

            if created_tick == -1:
                state['created_tick'] = tick
                self._ioc_orders[order_id] = tick
                continue

            if tick > created_tick:
                if state['remaining'] > 0:
                    state['status'] = 'cancelled'
                else:
                    state['status'] = 'filled'
                self.open_orders.pop(order_id, None)
                expired.append(order_id)

        for order_id in expired:
            self._ioc_orders.pop(order_id, None)

    def _finalize_ioc_orders(self):
        if self._last_tick == 0 or self._last_tick == self._last_finalized_tick:
            return

        to_remove: List[str] = []
        for order_id, created_tick in list(self._ioc_orders.items()):
            state = self.order_state.get(order_id)
            if not state or state['status'] != 'open':
                to_remove.append(order_id)
                continue

            if created_tick == -1:
                continue

            if created_tick <= self._last_tick:
                if state['remaining'] > 0:
                    state['status'] = 'cancelled'
                self.open_orders.pop(order_id, None)
                to_remove.append(order_id)

        for order_id in to_remove:
            self._ioc_orders.pop(order_id, None)

        self._last_finalized_tick = self._last_tick

    def _snapshot_order(self, order_id: str) -> Dict[str, Any]:
        state = self.order_state[order_id]
        return {
            'order_id': order_id,
            'direction': state['direction'],
            'price': state['price'],
            'original_quantity': state['original_quantity'],
            'remaining': state['remaining'],
            'filled_quantity': state['original_quantity'] - state['remaining'],
            'time_in_force': state['time_in_force'],
            'status': state['status'],
            'created_tick': state['created_tick'],
            'expiry_tick': state['expiry_tick']
        }