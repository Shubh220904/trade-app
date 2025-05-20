# app.py
import streamlit as st
import time
import numpy as np
from core.websocket_client import OKXWebSocketClient
from models.market_impact import MarketImpactCalculator
from models.slippage import SlippageModel
from models.maker_taker import MakerTakerPredictor
from config import FEE_TIERS, SYMBOL
import requests

def check_vpn_connection():
    try:
        response = requests.get("https://www.okx.com/api/v5/public/time", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    st.set_page_config(page_title="Crypto Trade Simulator", layout="wide")
    if 'running' not in st.session_state:
        st.session_state['running'] = False
    if 'client' not in st.session_state:
        st.session_state['client'] = OKXWebSocketClient()
    if 'last_update' not in st.session_state:
        st.session_state['last_update'] = time.time()
    if 'models_initialized' not in st.session_state:
        st.session_state['models_initialized'] = False
    # VPN Connection Check
    if not check_vpn_connection():
        st.error("""
        🔒 VPN Connection Required!
        1. Connect to your VPN
        2. Ensure access to OKX API
        3. Refresh this page
        """)
        return

    # Initialize session state
    # if 'running' not in st.session_state:
    #     st.session_state.update({
    #         'running': False,
    #         'client': OKXWebSocketClient(),
    #         'last_update': time.time(),
    #         'models_initialized': False
    #     })

    # Initialize models with error handling
    if not st.session_state.models_initialized:
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            status_text.markdown("🔄 Loading models...")
            progress_bar.progress(30)
            slippage_model = SlippageModel()
            slippage_model.load()
            progress_bar.progress(60)
            maker_taker_model = MakerTakerPredictor()
            maker_taker_model.load()
            progress_bar.progress(90)
            impact_model = MarketImpactCalculator()
            impact_model.load()
            st.session_state.models = {
                'slippage': slippage_model,
                'maker_taker': maker_taker_model,
                'impact': impact_model
            }
            progress_bar.progress(100)
            status_text.markdown("✅ Models loaded successfully!")
            st.session_state.models_initialized = True
            time.sleep(1)
            status_text.empty()
        except Exception as e:
            progress_bar.progress(100)
            status_text.error(f"""
            ❌ Model loading failed!
            Error: {str(e)}
            """)
            st.session_state.models_initialized = False
            return

    # Control Panel
    with st.sidebar:
        st.header("🎮 Control Panel")
    
        # Start/Stop controls
        col1, col2 = st.columns(2)
        with col1:
            start_btn = st.button("🚀 Start", help="Begin real-time simulation")
        with col2:
            stop_btn = st.button("🛑 Stop", help="Stop simulation")
    
        if start_btn and not st.session_state.running:
            st.session_state.running = True
            if not st.session_state.client.running:
                st.session_state.client.start()
    
        if stop_btn and st.session_state.running:
            st.session_state.running = False
            st.session_state.client.stop()
    
        # --- Input Parameters ---
        st.header("⚙️ Trade Parameters")
    
        # 1. Exchange (currently only OKX)
        exchange = st.selectbox(
            "Exchange",
            options=["OKX"],
            index=0,
            help="Select the exchange"
        )
    
        # 2. Spot Asset (symbol)
        spot_asset = st.text_input(
            "Spot Asset (Symbol)",
            value=SYMBOL,
            help="Enter the trading pair symbol, e.g., BTC-USDT"
        )
    
        # 3. Order Type (only 'market' supported)
        order_type = st.selectbox(
            "Order Type",
            options=["market"],
            index=0,
            help="Order type (only market orders supported)"
        )
    
        # 4. Quantity (~100 USD equivalent)
        quantity_usd = st.number_input(
            "Quantity (~USD)",
            min_value=1.0,
            max_value=100000.0,
            value=100.0,
            step=1.0,
            help="Order size in USD equivalent"
        )
    
        # 5. Volatility (market parameter)
        volatility = st.slider(
            "Volatility (market parameter, %)",
            min_value=0.1,
            max_value=10.0,
            value=2.0,
            step=0.1,
            help="Expected market volatility (%)"
        )
    
        # 6. Fee Tier
        fee_tier = st.selectbox(
            "Fee Tier",
            options=list(FEE_TIERS.keys()),
            help="Select your fee tier based on trading volume"
        )
    
    # Main Display
    st.header("📈 Real-Time Trading Metrics")
    
    # Create columns for metrics
    col1, col2 = st.columns(2)
    
    # Initialize metric placeholders
    metrics = {
        'slippage': col1.empty(),
        'fees': col1.empty(),
        'impact': col1.empty(),
        'cost': col2.empty(),
        'maker_taker': col2.empty(),
        'latency': col2.empty()
    }

    # Main simulation loop
    while st.session_state.running:
        try:
            loop_start = time.perf_counter()
            data_start = time.perf_counter()
            order_book = st.session_state.client.order_book
            
            if not order_book or order_book.mid_price == 0:
                time.sleep(0.5)
                continue
            
            # Convert USD to asset quantity using current mid price
            quantity = quantity_usd / order_book.mid_price
            # Calculate market features

            best_bid = max(order_book.bids.keys()) if order_book.bids else 0
            best_ask = min(order_book.asks.keys()) if order_book.asks else 0
            spread = (best_ask - best_bid) / order_book.mid_price if best_ask and best_bid else 0
            liquidity = order_book.get_liquidity_depth()
            
            # Prepare model inputs
            order_size_ratio = quantity / liquidity if liquidity > 0 else 0
            current_volatility = volatility / 100
            data_end = time.perf_counter()
            data_latency = (data_end - data_start) * 1000  # ms
            
            # Model predictions
            model_start = time.perf_counter()
            slippage = st.session_state.models['slippage'].predict(
                order_size_ratio, 
                current_volatility,
                spread
            )['linear']
            
            maker_prob = st.session_state.models['maker_taker'].predict_probability(
                quantity,
                spread
            )
            
            # Cost calculations
            order_value = quantity * order_book.mid_price
            fees = order_value * FEE_TIERS[fee_tier]['taker']
            market_impact = st.session_state.models['impact'].calculate_impact(
                quantity, 
                current_volatility,
                liquidity
            )
            net_cost = order_value + fees + (slippage * order_value) + (market_impact * order_value)
            model_end = time.perf_counter()
            model_latency = (model_end - model_start) * 1000  # ms

            # Latency calculation
            latency_ms = (time.time() - st.session_state.last_update) * 1000
            st.session_state.last_update = time.time()

            ui_start = time.perf_counter()
             
            

            # Update metrics display
            metrics['slippage'].metric(
                "Estimated Slippage", 
                f"{slippage*100:.2f}%",
                delta=f"Model: Linear Regression | Size Ratio: {order_size_ratio:.4f}"
            )
            
            metrics['fees'].metric(
                "Transaction Fees", 
                f"${fees:,.2f}",
                delta=f"Taker Fee: {FEE_TIERS[fee_tier]['taker']*100:.2f}% | Value: ${order_value:,.2f}"
            )
            
            metrics['impact'].metric(
                "Market Impact", 
                f"${market_impact * order_value:,.2f}",
                delta=f"Impact: {market_impact*100:.2f}% | Liquidity: {liquidity:.2f} BTC"
            )
            
            metrics['cost'].metric(
                "Total Estimated Cost", 
                f"${net_cost:,.2f}",
                delta=f"Breakdown: Price({order_value:,.2f}) + Fees({fees:,.2f}) + Slippage({slippage*order_value:,.2f}) + Impact({market_impact*order_value:,.2f})"
            )
            
            metrics['maker_taker'].metric(
                "Maker/Taker Probability", 
                f"{maker_prob*100:.1f}% Maker",
                delta=f"{100 - maker_prob*100:.1f}% Taker | Spread: {spread*100:.2f}%"
            )

            ui_end = time.perf_counter()
            ui_latency = (ui_end - ui_start) * 1000  # ms

            loop_end = time.perf_counter()
            loop_latency = (loop_end - loop_start) * 1000  # ms
            
            metrics['latency'].metric(
                "System Latency", 
                
                f"{loop_latency:.1f} ms",
                delta=f"Data: {data_latency:.1f} ms | Model: {model_latency:.1f} ms | UI: {ui_latency:.1f} ms"
            )

            time.sleep(0.5)  # Update interval
            

        except Exception as e:
            st.error(f"⚠️ Simulation Error: {str(e)}")
            st.session_state.running = False
            if st.session_state.client.running:
                st.session_state.client.stop()
            break

if __name__ == "__main__":
    main()