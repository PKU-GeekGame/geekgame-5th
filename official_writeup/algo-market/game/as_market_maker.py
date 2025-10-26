import math
from typing import List, Dict, Any, Optional
from exchange import Participant, Order, Trade
import random


class ASMarketMaker(Participant):
    """Simplified Avellaneda & Stoikov market maker."""

    def __init__(
        self,
        exchange,
        participant_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(exchange, participant_id)
        params = parameters.copy() if parameters else {}

        # Model parameters
        self.gamma = params.get('gamma', 0.1)
        self.horizon = params.get('horizon', 1.0)
        self.kappa = max(params.get('kappa', 5), 1e-6)
        self.base_sigma = max(params.get('base_sigma', 0.2), 1e-6)
        self.min_sigma = max(params.get('min_sigma', 0.01), 1e-6)
        self.sigma_window = max(int(params.get('sigma_window', 50)), 1)
        self.order_size = max(int(params.get('order_size', 200)), 1)
        self.news_vol_sensitivity = params.get('news_vol_sensitivity', 2.0)
        self.slippage_limit = params.get('slippage_limit', 0.5)
        self.sigma_lambda = params.get('sigma_lambda', 0.94)
        self.last_sigma = self.base_sigma

        # State variables
        self.cash = 0.0
        self.stock = 0.0
        self.position_history = []
        self.news_vol_multiplier = 1.0

    def get_orders(self, current_price: float, tick: int) -> List[Order]:
        orders: List[Order] = []

        mid_price = self._get_mid_price(current_price)
        sigma = self._estimate_volatility()
        if sigma <= 0:
            sigma = self.base_sigma

        reservation_price = self._compute_reservation_price(mid_price, sigma)
        half_spread = self._compute_half_spread(sigma)

        bid_price = max(0.01, reservation_price - half_spread)
        ask_price = max(bid_price + 0.01, reservation_price + half_spread)

        bid_price = max(0.01, bid_price)
        ask_price = max(0.01, ask_price)

        base_size = self.order_size
        if sigma > 0.05:
            base_size = max(1, int(self.order_size * 0.05 / sigma))

        for i in range(10):
            fact = i if i<5 else 4+2**(i-4)
            size = 1 if i<5 else (i-4)
            orders.append(Order(
                participant_id=self.participant_id,
                price=bid_price-fact*half_spread,
                quantity=int(base_size * size*(1+0.1*random.random())),
                order_type='buy'
            ))
            orders.append(Order(
                participant_id=self.participant_id,
                price=ask_price+fact*half_spread,
                quantity=-int(base_size * size*(1+0.1*random.random())),
                order_type='sell'
            ))

        self.news_vol_multiplier = 0.01 + self.news_vol_multiplier*0.99

        print(f"({tick})ASM: spread {ask_price-bid_price:.2f}, sigma {sigma:.4f}, vol_mult {self.news_vol_multiplier:.4f}, portfolio {self.get_portfolio_value(current_price):.2f}, stock {self.stock}, mid_price {reservation_price:.2f}, ref_price {mid_price:.2f}")

        return orders

    def on_trade(self, trade: Trade, side: str):
        if side == "buy":
            cash_change = trade.price * trade.quantity
            self.cash -= cash_change
            self.stock += trade.quantity
        elif side == "sell":
            cash_change = trade.price * trade.quantity
            self.cash += cash_change
            self.stock -= trade.quantity


    def on_news(self, rating: float):
        # Adjust volatility multiplier in response to news sentiment
        adjustment = 1.0 + self.news_vol_sensitivity * abs(rating)
        if adjustment <= 0:
            adjustment = 0.1
        self.news_vol_multiplier *= adjustment
        self.news_vol_multiplier = max(0.25, min(4.0, self.news_vol_multiplier))

    def get_portfolio_value(self, current_price: float) -> float:
        return self.cash + self.stock * current_price

    def _get_mid_price(self, current_price: float) -> float:
        last_price = self.exchange.last_price
        if last_price <= 0:
            last_price = current_price
        return max(0.01, last_price)

    def _estimate_volatility(self) -> float:
        prices = self.exchange.get_price_history()
        if len(prices) < 2:
            self.last_sigma = self.base_sigma
            return self.last_sigma * self.news_vol_multiplier
        log_return = math.log(prices[-1] / prices[-2])
        self.last_sigma = (self.sigma_lambda * self.last_sigma ** 2 + (1 - self.sigma_lambda) * log_return ** 2 * 240) ** 0.5
        return self.last_sigma * self.news_vol_multiplier


    def _compute_reservation_price(self, mid_price: float, sigma: float) -> float:
        reservation_adjustment = self.stock * self.gamma * (sigma ** 2) * self.horizon
        return mid_price - reservation_adjustment

    def _compute_half_spread(self, sigma: float) -> float:
        spread_component = self.gamma * (sigma ** 2) * self.horizon / 2 * 100
        liquidity_component = math.log1p(self.gamma / self.kappa) / max(self.gamma, 1e-6)
        print(spread_component, liquidity_component)
        half_spread = max(0.01 / 2, spread_component + liquidity_component)
        return half_spread