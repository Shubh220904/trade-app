import numpy as np
from data.historical_data import fetch_historical_trades, fetch_order_book_snapshots
from models.slippage import SlippageModel
from models.maker_taker import MakerTakerPredictor
from models.market_impact import MarketImpactCalculator

symbol = "BTC-USDT"
print("Fetching historical trades...")
trades = fetch_historical_trades(symbol, 1000)
if trades.empty:
    raise RuntimeError("No historical data available for training.")

# Dummy feature engineering for demonstration
order_size_ratios = trades['quantity'] / trades['quantity'].max()
volatility = np.full(len(trades), 0.02)
spread = np.full(len(trades), 0.001)
X = np.column_stack([order_size_ratios, volatility, spread])
y_slippage = (trades['price'] - trades['price'].mean()) / trades['price'].mean()
y_maker_taker = (trades['side'] == 'buy').astype(int).values

print("Training slippage model...")
slippage_model = SlippageModel()
slippage_model.train(X, y_slippage)

print("Training maker/taker model...")
maker_taker_model = MakerTakerPredictor()
maker_taker_model.train(X[:, :2], y_maker_taker)

print("Saving market impact model parameters...")
impact_model = MarketImpactCalculator()
impact_model.train(0.1)  # Save risk_aversion param

print("All models trained and saved.")