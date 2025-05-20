class OrderBook:
    def __init__(self):
        self.bids = {}
        self.asks = {}
        self.mid_price = 0.0
        
    def update(self, data):
        if 'data' in data:
            book_data = data['data'][0]
            self._update_side(self.bids, book_data['bids'])
            self._update_side(self.asks, book_data['asks'])
            self._calculate_mid_price()
            
    def _update_side(self, side, entries):
        for price, quantity, *_ in entries:   
            price = float(price)
            quantity = float(quantity)
            
            if quantity == 0:
                side.pop(price, None)
            else:
                side[price] = quantity  # Store as quantity instead of qty
    
    def _calculate_mid_price(self):
        best_bid = max(self.bids.keys()) if self.bids else 0
        best_ask = min(self.asks.keys()) if self.asks else 0
        self.mid_price = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
    
    def get_liquidity_depth(self, depth=0.1):
        upper = self.mid_price * (1 + depth)
        lower = self.mid_price * (1 - depth)
        
        bid_liq = sum(quantity for p, quantity in self.bids.items() if lower <= p <= upper)
        ask_liq = sum(quantity for p, quantity in self.asks.items() if lower <= p <= upper)
        
        return bid_liq + ask_liq