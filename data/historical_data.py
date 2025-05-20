import requests
import pandas as pd
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any

OKX_REST_URL = "https://www.okx.com/api/v5"

def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def validate_timestamp(ts) -> pd.Timestamp:
    """Convert a millisecond timestamp to pandas datetime, or NaT on failure."""
    try:
        return pd.to_datetime(int(ts), unit='ms')
    except (OverflowError, ValueError, TypeError):
        return pd.NaT

def safe_float_conversion(value) -> float:
    """Safely convert a value to float, return 0.0 on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def fetch_historical_trades(symbol: str, limit: int = 1000) -> pd.DataFrame:
    """
    Fetch historical trades for a given symbol from OKX.
    Returns a pandas DataFrame with timestamp, price, quantity, and side.
    """
    session = create_session()
    try:
        response = session.get(
            f"{OKX_REST_URL}/market/trades",
            params={"instId": symbol, "limit": limit},
            timeout=10
        )
        response.raise_for_status()
        data = response.json().get('data', [])
        if not data:
            logging.warning(f"No trade data returned for {symbol}")
            return pd.DataFrame(columns=['timestamp', 'price', 'quantity', 'side'])
        return pd.DataFrame([{
            'timestamp': validate_timestamp(trade.get('ts')),
            'price': safe_float_conversion(trade.get('px')),
            'quantity': safe_float_conversion(trade.get('sz')),
            'side': trade.get('side', 'unknown')
        } for trade in data])
    except Exception as e:
        logging.error(f"Failed to fetch trades for {symbol}: {str(e)}")
        return pd.DataFrame(columns=['timestamp', 'price', 'quantity', 'side'])

def fetch_order_book_snapshots(symbol: str, depth: int = 10) -> Dict[str, Any]:
    """
    Fetch order book snapshot for a given symbol from OKX.
    Returns a dict with bids, asks (as DataFrames), and timestamp.
    """
    session = create_session()
    try:
        response = session.get(
            f"{OKX_REST_URL}/market/books",
            params={
                "instId": symbol,
                "sz": depth
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json().get('data', [{}])
        if not data or not isinstance(data, list) or not data[0]:
            logging.warning(f"No order book data returned for {symbol}")
            return {
                'bids': pd.DataFrame(columns=['price', 'quantity']),
                'asks': pd.DataFrame(columns=['price', 'quantity']),
                'timestamp': pd.NaT
            }
        book = data[0]
        bids = book.get('bids', [])
        asks = book.get('asks', [])
        ts = book.get('ts', None)
        return {
            'bids': pd.DataFrame(
                [(safe_float_conversion(p), safe_float_conversion(q)) for p, q, *_ in bids],
                columns=['price', 'quantity']
            ),
            'asks': pd.DataFrame(
                [(safe_float_conversion(p), safe_float_conversion(q)) for p, q, *_ in asks],
                columns=['price', 'quantity']
            ),
            'timestamp': validate_timestamp(ts)
        }
    except Exception as e:
        logging.error(f"Order book fetch failed for {symbol}: {str(e)}")
        return {
            'bids': pd.DataFrame(columns=['price', 'quantity']),
            'asks': pd.DataFrame(columns=['price', 'quantity']),
            'timestamp': pd.NaT
        }