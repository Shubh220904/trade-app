import joblib
import os

MODEL_PATH = "models/market_impact_model.joblib"

class MarketImpactCalculator:
    def __init__(self, risk_aversion=0.1):
        self.risk_aversion = risk_aversion

    def train(self, params):
        joblib.dump(params, MODEL_PATH)

    def load(self):
        if os.path.exists(MODEL_PATH):
            self.risk_aversion = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError("Market impact model not found. Please train it first.")

    def calculate_impact(self, order_size, volatility, liquidity):
        temporary_impact = (order_size / liquidity) * volatility
        permanent_impact = 0.1 * temporary_impact
        return temporary_impact + permanent_impact