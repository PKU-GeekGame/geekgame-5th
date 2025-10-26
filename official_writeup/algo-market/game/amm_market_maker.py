import random
import math
from typing import List
from exchange import Participant, Order, Trade


class AMMMarketMaker(Participant):
    def __init__(self, exchange, participant_id: str, initial_cash: float, initial_stock: int):
        super().__init__(exchange, participant_id)
        self.cash = initial_cash
        self.stock = initial_stock
        self.k = initial_cash * initial_stock  # x * y = k constant product formula
        self.position_history = []
        
    def get_orders(self, current_price: float, tick: int) -> List[Order]:
        """Generate orders at different price levels based on AMM formula"""
        orders = []
        
        # Use current market price as reference for order placement
        market_price = self.get_reserve_price() if self.stock > 0 else current_price
        
        # Define price levels relative to market price (±1%, ±2%, ±3%, ±5%)
        price_levels = [
            0.995, 0.99, 0.97, 0.95, 0.90,
            1.005, 1.01, 1.03, 1.05, 1.10
        ]
        
        # Track cumulative effect as orders at better prices execute first
        simulated_cash = self.cash
        simulated_stock = self.stock
        initial_k = simulated_cash * simulated_stock if simulated_cash > 0 and simulated_stock > 0 else 0

        buy_levels = sorted([r for r in price_levels if r < 1], reverse=True)
        sell_levels = sorted([r for r in price_levels if r > 1])

        for price_ratio in buy_levels:
            target_price = market_price * price_ratio
            # theoretical_buy_amount = max(0.0, simulated_cash / target_price - simulated_stock)
            theoretical_buy_amount = max(0.0, (simulated_cash * simulated_stock / target_price) ** 0.5 - simulated_stock)
            order_quantity = int(theoretical_buy_amount)
            
            if order_quantity >= 1:
                orders.append(Order(
                    participant_id=self.participant_id,
                    price=target_price,
                    quantity=order_quantity,
                    order_type="buy"
                ))
                simulated_cash -= target_price * order_quantity
                simulated_stock += order_quantity
                assert initial_k <= simulated_cash * simulated_stock, "Invariant k should not decrease on buys"
                # print(initial_k, simulated_cash * simulated_stock)
                        
        simulated_cash = self.cash
        simulated_stock = self.stock
        for price_ratio in sell_levels:
            target_price = market_price * price_ratio
            # theoretical_sell_amount = max(0.0, simulated_stock - simulated_cash / target_price)
            theoretical_sell_amount = max(0.0, simulated_stock - (simulated_cash * simulated_stock / target_price) ** 0.5)
            order_quantity = int(theoretical_sell_amount)
            
            if order_quantity >= 1:
                orders.append(Order(
                    participant_id=self.participant_id,
                    price=target_price,
                    quantity=-order_quantity,  # Negative for sell
                    order_type="sell"
                ))
                simulated_cash += target_price * order_quantity
                simulated_stock -= order_quantity
                assert initial_k <= simulated_cash * simulated_stock, "Invariant k should not decrease on sells"
                # print(initial_k, simulated_cash * simulated_stock)
        
        return orders

    def on_trade(self, trade: Trade, side: str):
        """Update AMM reserves when a trade occurs"""
        if side == "buy":
            cash_spent = trade.price * trade.quantity
            self.cash -= cash_spent
            self.stock += trade.quantity

        elif side == "sell":
            # We sold stock  
            cash_received = trade.price * trade.quantity
            self.cash += cash_received
            self.stock -= trade.quantity
        
        # Update k to maintain the invariant (in practice, k might change with fees)
        if self.stock > 0 and self.cash > 0:
            self.k = self.cash * self.stock
        
    
    def get_portfolio_value(self, current_price: float) -> float:
        """Calculate total portfolio value at current price"""
        return self.cash + (self.stock * current_price)
    
    def get_reserve_price(self) -> float:
        """Get current reserve price from AMM formula"""
        if self.stock > 0:
            return self.cash / self.stock
        return 0.0
    
    def on_news(self, rating: float):
        """Adjust strategy based on news sentiment (rating between -1 and 1)"""
        pass