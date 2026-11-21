import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Daily Stock Bounce Comparator", layout="wide")

st.title("📈 Daily Stock Bounce Comparator")
st.caption("Pre-Market • Relative Volume • Bounce Score • RSI • Support/Resistance • Pivot Points • Volume Levels • Moving Averages")

# Sidebar
st.sidebar.header("Settings")
tickers_input = st.sidebar.text_input(
    "Enter tickers (comma separated)",
    value="NVDA, AMD, INTC"
)
tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

if len(tickers) < 2:
    st.warning("Please enter at least 2 tickers.")
    st.stop()

if len(tickers) > 5:
    tickers = tickers[:5]

analyze = st.sidebar.button("🔍 Analyze Stocks", type="primary")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_premarket_data(ticker):
    try:
        info = yf.Ticker(ticker).info
        pre_price = info.get("preMarketPrice")
        pre_change_pct = info.get("preMarketChangePercent")
        regular_price = info.get("regularMarketPreviousClose") or info.get("previousClose")
        
        if pre_price and regular_price:
            change_pct = ((pre_price - regular_price) / regular_price) * 100
            return {
                "Pre-Market Price": round(pre_price, 2),
                "Pre-Market %": round(change_pct, 2)
            }
        elif pre_change_pct is not None:
            return {
                "Pre-Market Price": round(pre_price, 2) if pre_price else None,
                "Pre-Market %": round(pre_change_pct, 2)
            }
    except:
        pass
    return {"Pre-Market Price": None, "Pre-Market %": None}

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        
        if hist.empty or len(hist) < 50:
            return None
        
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        day_change = ((current_price - prev_close) / prev_close) * 100
        
        premarket = get_premarket_data(ticker)
        
        today_volume = hist['Volume'].iloc[-1]
        avg_volume_20 = hist['Volume'].tail(20).mean()
        rel_volume = today_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        
        five_day_change = ((current_price - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100
        
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.tail(10).std() * np.sqrt(252) * 100
        
        rsi = calculate_rsi(hist['Close'], period=14)
        
        high_20 = hist['High'].tail(20).max()
        distance_from_high = ((high_20 - current_price) / high_20) * 100
        oversold_score = min(100, max(0, 
            (abs(min(day_change, 0)) * 3) + 
            (distance_from_high * 0.8) + 
            (rel_volume * 8)
        ))
        
        bounce_score = (
            (rel_volume * 25) +
            (abs(min(day_change, 0)) * 4) +
            (oversold_score * 0.4) +
            (max(0, -five_day_change) * 1.5)
        )
        
        recent_support = hist['Low'].tail(10).min()
        recent_resistance = hist['High'].tail(10).max()
        
        prev_high = hist['High'].iloc[-2]
        prev_low = hist['Low'].iloc[-2]
        prev_close_pp = hist['Close'].iloc[-2]
        
        pivot = (prev_high + prev_low + prev_close_pp) / 3
        r1 = (2 * pivot) - prev_low
        s1 = (2 * pivot) - prev_high
        
        recent_hist = hist.tail(15)
        high_vol_idx = recent_hist['Volume'].idxmax()
        high_vol_price = recent_hist.loc[high_vol_idx, 'Close']
        
        recent_10 = hist.tail(10)
        vwap = (recent_10['Close'] * recent_10['Volume']).sum() / recent_10['Volume'].sum()
        
        sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        
        dist_sma20 = ((current_price - sma_20) / sma_20) * 100
        dist_sma50 = ((current_price - sma_50) / sma_50) * 100
        
        return {
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "Day %": round(day_change, 2),
            "Pre-Market Price": premarket["Pre-Market Price"],
            "Pre-Market %": premarket["Pre-Market %"],
            "Rel Volume": round(rel_volume, 2),
            "5D %": round(five_day_change, 2),
            "RSI": round(rsi, 1),
            "Volatility %": round(volatility, 1),
            "Oversold": round(oversold_score, 1),
            "Bounce Score": round(bounce_score, 1),
            "Support": round(recent_support, 2),
            "Resistance": round(recent_resistance, 2),
            "Pivot": round(pivot, 2),
            "R1": round(r1, 2),
            "S1": round(s1, 2),
            "High Vol Level": round(high_vol_price, 2),
            "VWAP (10D)": round(vwap, 2),
            "SMA 20": round(sma_20, 2),
            "Dist SMA20 %": round(dist_sma20, 2),
            "SMA 50": round(sma_50, 2),
            "Dist SMA50 %": round(dist_sma50, 2)
        }
    except Exception as e:
        st.error(f"Error with {ticker}: {e}")
        return None

if analyze:
    with st.spinner("Fetching data (including pre-market)..."):
        results = []
        for ticker in tickers:
            data = get_stock_data(ticker)
            if data:
                results.append(data)
        
        if not results:
            st.error("No data retrieved.")
            st.stop()
        
        df = pd.DataFrame(results)
        df = df.sort_values("Bounce Score", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1
        
        # Pre-Market
        st.subheader("🌅 Pre-Market Snapshot")
        pre_cols = ["Ticker", "Price", "Pre-Market Price", "Pre-Market %"]
        st.dataframe(
            df[pre_cols].style.format({
                "Price": "{:.2f}",
                "Pre-Market Price": "{:.2f}",
                "Pre-Market %": "{:.2f}%"
            }, na_rep="—"),
            use_container_width=True
        )
        
        # Main Comparison
        st.subheader("📊 Main Comparison")
        main_cols = ["Rank", "Ticker", "Price", "Day %", "Rel Volume", "5D %", "RSI", "Volatility %", "Oversold", "Bounce Score"]
        st.dataframe(
            df[main_cols].style.format({
                "Price": "{:.2f}",
                "Day %": "{:.2f}%",
                "Rel Volume": "{:.2f}x",
                "5D %": "{:.2f}%",
                "RSI": "{:.1f}",
                "Volatility %": "{:.1f}%",
                "Oversold": "{:.1f}",
                "Bounce Score": "{:.1f}"
            }).background_gradient(subset=["Bounce Score"], cmap="RdYlGn"),
            use_container_width=True
        )
        
        winner = df.iloc[0]
        st.success(f"**Best Bounce Candidate: {winner['Ticker']}**  |  Bounce Score: {winner['Bounce Score']}")
        
        # Support / Resistance + Pivots
        st.subheader("📍 Support, Resistance & Pivot Points")
        sr_cols = ["Ticker", "Price", "Support", "S1", "Pivot", "R1", "Resistance"]
        st.dataframe(
            df[sr_cols].style.format({
                "Price": "{:.2f}",
                "Support": "{:.2f}",
                "S1": "{:.2f}",
                "Pivot": "{:.2f}",
                "R1": "{:.2f}",
                "Resistance": "{:.2f}"
            }),
            use_container_width=True
        )
        
        # Volume Levels
        st.subheader("📊 Volume-Based Key Levels")
        vol_cols = ["Ticker", "Price", "High Vol Level", "VWAP (10D)"]
        st.dataframe(
            df[vol_cols].style.format({
                "Price": "{:.2f}",
                "High Vol Level": "{:.2f}",
                "VWAP (10D)": "{:.2f}"
            }),
            use_container_width=True
        )
        
        # Moving Averages
        st.subheader("📈 Moving Averages")
        ma_cols = ["Ticker", "Price", "SMA 20", "Dist SMA20 %", "SMA 50", "Dist SMA50 %"]
        st.dataframe(
            df[ma_cols].style.format({
                "Price": "{:.2f}",
                "SMA 20": "{:.2f}",
                "Dist SMA20 %": "{:.2f}%",
                "SMA 50": "{:.2f}",
                "Dist SMA50 %": "{:.2f}%"
            }),
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### Quick Guide")
        st.markdown("""
        - **RSI < 30** → Oversold
        - **Pre-Market %** → Early session direction
        - **SMA 20 / SMA 50** → Dynamic support/resistance
        - **S1 / Pivot / R1** → Classic pivot points
        """)
        
        st.caption(f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by yfinance")

else:
    st.info("Enter tickers on the left and click **Analyze Stocks**")
