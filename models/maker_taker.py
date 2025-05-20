import numpy as np
import joblib
import os
from sklearn.linear_model import LogisticRegression

MODEL_PATH = "models/maker_taker_model.joblib"

class MakerTakerPredictor:
    def __init__(self):
        self.model = None

    def train(self, X, y):
        self.model = LogisticRegression()
        self.model.fit(X, y)
        joblib.dump(self.model, MODEL_PATH)

    def load(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError("Maker/Taker model not found. Please train it first.")

    def predict_probability(self, order_size, normalized_price):
        if self.model is None:
            self.load()
        X = np.array([[order_size, normalized_price]])
        return self.model.predict_proba(X)[0][1]