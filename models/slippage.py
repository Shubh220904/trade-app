import numpy as np
import pandas as pd
import joblib
import os
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

MODEL_PATH = "models/slippage_model.joblib"

class SlippageModel:
    def __init__(self):
        self.linear_model = None
        self.quantile_model = None

    def train(self, X, y):
        self.linear_model = LinearRegression()
        self.linear_model.fit(X, y)
        self.quantile_model = RandomForestRegressor()
        self.quantile_model.fit(X, y)
        joblib.dump((self.linear_model, self.quantile_model), MODEL_PATH)

    def load(self):
        if os.path.exists(MODEL_PATH):
            self.linear_model, self.quantile_model = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError("Slippage model not found. Please train it first.")

    def predict(self, order_size_ratio, volatility, spread):
        if self.linear_model is None or self.quantile_model is None:
            self.load()
        X = np.array([[order_size_ratio, volatility, spread]])
        return {
            'linear': self.linear_model.predict(X)[0],
            'quantile': np.percentile(self.quantile_model.predict(X), 0.95)
        }