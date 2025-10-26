import math
import random
from typing import List, Dict, Any, Optional
from exchange import Participant, Order, Trade


class RetailTrader(Participant):
    def __init__(
        self,
        exchange,
        participant_id: str,
        initial_cash: float,
        initial_stock: int,
    behavior_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(exchange, participant_id)
        self.cash = initial_cash
        self.stock = initial_stock
        self.initial_cash = initial_cash
        self.initial_stock = initial_stock
        self.last_trade_price = 100.0
        self.trade_history = []
        self.position_history = []

        config = behavior_config.copy() if behavior_config else {}
        current_reference_price = exchange.get_current_price()

        # Behavioural parameters (configurable per trader)
        self.expected_price = config.get('expected_price', current_reference_price)
        self.base_trade_prob = config.get('base_trade_prob', 0.05)
        self.max_trade_prob = min(1.0, config.get('max_trade_prob', 0.9))
        self.price_sensitivity = config.get('price_sensitivity', 5.0)
        self.position_sensitivity = config.get('position_sensitivity', 0.5)
        self.direction_price_weight = config.get('direction_price_weight', 1.0)
        self.direction_position_weight = config.get('direction_position_weight', 0.1)
        self.direction_noise = config.get('direction_noise', 0.2)
        self.size_price_weight = config.get('size_price_weight', 0.8)
        self.size_position_weight = config.get('size_position_weight', 0.2)
        self.size_randomness = config.get('size_randomness', 0.3)
        self.min_size_fraction = config.get('min_size_fraction', 0.1)
        self.target_stock_ratio = config.get('target_stock_ratio', 0.9)
        self.adaptation_rate = config.get('adaptation_rate', 0.05)
        self.news_sensitivity = config.get('news_sensitivity', 1.0)
        self.max_order_size = config.get('max_order_size', 500)
        self.slippage_pct = config.get('slippage_pct', 0.01)
        
    def get_orders(self, current_price: float, tick: int) -> List[Order]:
        """Generate orders based on retail trader behavior"""
        orders = []
        
        # Update last trade price
        self.last_trade_price = current_price
        
        portfolio_value = self.cash + (self.stock * current_price)
        if portfolio_value <= 0:
            self._adapt_expectations(current_price)
            return orders
        
        # print(f"Trader {self.participant_id} Cash: {self.cash:.2f}, Stock: {self.stock}, Current Price: {current_price:.2f}, Expected Price: {self.expected_price:.2f}")

        price_deviation = 0.0
        if self.expected_price > 0:
            price_deviation = (current_price - self.expected_price) / self.expected_price

        stock_value = self.stock * current_price
        stock_ratio = stock_value / portfolio_value if portfolio_value > 0 else 0.0
        position_deviation = stock_ratio - self.target_stock_ratio

        trade_prob = self.base_trade_prob
        trade_prob += self.price_sensitivity * abs(price_deviation)
        trade_prob += self.position_sensitivity * abs(position_deviation)
        trade_prob = max(0.0, min(self.max_trade_prob, trade_prob))

        if random.random() >= trade_prob:
            self._adapt_expectations(current_price)
            return orders

        direction_signal = 0.0
        direction_signal += -self.direction_price_weight * price_deviation * 5.0
        direction_signal += -self.direction_position_weight * position_deviation * 5.0
        direction_signal += random.gauss(0, self.direction_noise)
        buy_probability = 1.0 / (1.0 + math.exp(-direction_signal))
        direction = "buy" if random.random() < buy_probability else "sell"

        intensity = (
            self.size_price_weight * abs(price_deviation) +
            self.size_position_weight * abs(position_deviation)
        )
        intensity = max(0.0, min(1.0, intensity))
        randomized_scale = (
            self.min_size_fraction + (1 - self.min_size_fraction) * intensity
        )
        randomized_scale *= random.uniform(1 - self.size_randomness, 1 + self.size_randomness)
        randomized_scale = max(0.05, min(1.0, randomized_scale))
        desired_quantity = max(1, int(self.max_order_size * randomized_scale))

        order = self._create_order(direction, current_price, desired_quantity)
        if order:
            orders.append(order)
        
        self._adapt_expectations(current_price)
        return orders

    def _create_order(self, direction: str, current_price: float, requested_quantity: int) -> Order:
        """Create a simple market-adjacent order in the requested direction."""
        if requested_quantity <= 0:
            return None

        order_price = current_price * (1 + self.slippage_pct if direction == "buy" else 1 - self.slippage_pct)
        if direction == "buy":
            max_shares = int(self.cash / order_price)
            if max_shares <= 0:
                return None

            order_size = min(requested_quantity, max_shares)
            if order_size <= 0:
                return None
            return Order(
                participant_id=self.participant_id,
                price=order_price,
                quantity=order_size,
                order_type="buy"
            )

        if direction == "sell":
            if self.stock <= 0:
                return None

            order_size = min(requested_quantity, self.stock)
            if order_size <= 0:
                return None
            return Order(
                participant_id=self.participant_id,
                price=order_price,
                quantity=-order_size,
                order_type="sell"
            )

        return None

    def _adapt_expectations(self, current_price: float):
        if self.adaptation_rate <= 0:
            return
        self.expected_price += self.adaptation_rate * (current_price - self.expected_price)
    
    def on_trade(self, trade: Trade, side: str):
        """Update portfolio when a trade occurs"""
        if side == "buy":
            # We bought stock
            cash_spent = trade.price * trade.quantity
            self.cash -= cash_spent
            self.stock += trade.quantity

        elif side == "sell":
            # We sold stock
            cash_received = trade.price * trade.quantity
            self.cash += cash_received
            self.stock -= trade.quantity

    def on_news(self, rating: float):
        """Adjust expectations based on external news sentiment."""
        if self.expected_price <= 0:
            return
        adjustment = 1 + self.news_sensitivity * rating
        if adjustment <= 0:
            adjustment = 0.01
        self.expected_price *= adjustment
        # print(f"Trader {self.participant_id} adjusted expected price to {self.expected_price:.2f} based on news rating {rating}")
    
    def get_portfolio_value(self, current_price: float) -> float:
        """Calculate total portfolio value at current price"""
        return self.cash + (self.stock * current_price)
    
    def get_performance_metrics(self, current_price: float) -> dict:
        """Get performance metrics"""
        initial_value = self.initial_cash + (self.initial_stock * current_price)
        current_value = self.get_portfolio_value(current_price)
        total_return = (current_value - initial_value) / initial_value * 100
        
        return {
            'current_value': current_value,
            'initial_value': initial_value,
            'total_return_pct': total_return,
            'cash': self.cash,
            'stock': self.stock,
            'num_trades': len(self.trade_history)
        }