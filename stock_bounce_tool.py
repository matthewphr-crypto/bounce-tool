import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Daily Stock Bounce Comparator", layout="wide")

st.title("📈 Daily Stock Bounce Comparator")
st.caption("Yahoo News • Google News • Earnings • Short Interest • Options • Sector • 1-Min Volume • Technicals")

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
        regular_price = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if pre_price and regular_price:
            change_pct = ((pre_price - regular_price) / regular_price) * 100
            return {"Pre-Market Price": round(pre_price, 2), "Pre-Market %": round(change_pct, 2)}
    except:
        pass
    return {"Pre-Market Price": None, "Pre-Market %": None}

def get_1min_volume(ticker):
    try:
        hist_1m = yf.Ticker(ticker).history(period="1d", interval="1m")
        if hist_1m.empty:
            return {"1Min Vol": None, "Avg 1Min Vol": None, "Rel 1Min Vol": None}
        latest = hist_1m['Volume'].iloc[-1]
        avg = hist_1m['Volume'].mean()
        return {
            "1Min Vol": int(latest),
            "Avg 1Min Vol": int(avg),
            "Rel 1Min Vol": round(latest / avg, 2) if avg > 0 else 0
        }
    except:
        return {"1Min Vol": None, "Avg 1Min Vol": None, "Rel 1Min Vol": None}

def get_extra_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Yahoo News
        yahoo_news = "No recent news"
        try:
            news = stock.news[:2] if hasattr(stock, 'news') and stock.news else []
            if news:
                titles = [n.get('title', '')[:60] for n in news if n.get('title')]
                if titles:
                    yahoo_news = " | ".join(titles)
        except:
            pass
        
        # Google News link
        news_link = f"https://www.google.com/search?q={ticker}+stock+news&tbm=nws"
        
        # Earnings
        earnings = info.get("earningsTimestamp") or info.get("earningsDate")
        earnings_date = datetime.fromtimestamp(earnings).strftime("%Y-%m-%d") if earnings else "N/A"
        
        # Short interest
        short_pct = info.get("shortPercentOfFloat")
        short_interest = f"{short_pct*100:.1f}%" if short_pct else "N/A"
        
        # Options / Put-Call
        try:
            options = stock.option_chain()
            calls = options.calls['volume'].sum() if not options.calls.empty else 0
            puts = options.puts['volume'].sum() if not options.puts.empty else 0
            pc_ratio = round(puts / calls, 2) if calls > 0 else "N/A"
        except:
            pc_ratio = "N/A"
        
        # Sector
        sector = info.get("sector", "N/A")
        
        return {
            "Yahoo News": yahoo_news,
            "Google News": news_link,
            "Earnings Date": earnings_date,
            "Short Interest %": short_interest,
            "Put/Call Ratio": pc_ratio,
            "Sector": sector
        }
    except:
        return {
            "Yahoo News": "N/A",
            "Google News": f"https://www.google.com/search?q={ticker}+stock+news&tbm=nws",
            "Earnings Date": "N/A",
            "Short Interest %": "N/A",
            "Put/Call Ratio": "N/A",
            "Sector": "N/A"
        }

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
        vol_1m = get_1min_volume(ticker)
        extra = get_extra_data(ticker)
        
        today_volume = hist['Volume'].iloc[-1]
        avg_volume_20 = hist['Volume'].tail(20).mean()
        rel_volume = today_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        
        five_day_change = ((current_price - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.tail(10).std() * np.sqrt(252) * 100
        rsi = calculate_rsi(hist['Close'], period=14)
        
        high_20 = hist['High'].tail(20).max()
        distance_from_high = ((high_20 - current_price) / high_20) * 100
        oversold_score = min(100, max(0, (abs(min(day_change, 0)) * 3) + (distance_from_high * 0.8) + (rel_volume * 8)))
        
        bounce_score = (rel_volume * 25) + (abs(min(day_change, 0)) * 4) + (oversold_score * 0.4) + (max(0, -five_day_change) * 1.5)
        
        recent_support = hist['Low'].tail(10).min()
        recent_resistance = hist['High'].tail(10).max()
        
        prev_high = hist['High'].iloc[-2]
        prev_low = hist['Low'].iloc[-2]
        prev_close_pp = hist['Close'].iloc[-2]
        pivot = (prev_high + prev_low + prev_close_pp) / 3
        r1 = (2 * pivot) - prev_low
        s1 = (2 * pivot) - prev_high
        
        recent_hist = hist.tail(15)
        high_vol_price = recent_hist.loc[recent_hist['Volume'].idxmax(), 'Close']
        recent_10 = hist.tail(10)
        vwap = (recent_10['Close'] * recent_10['Volume']).sum() / recent_10['Volume'].sum()
        
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
        
        return {
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "Day %": round(day_change, 2),
            "1Min Vol": vol_1m["1Min Vol"],
            "Rel 1Min Vol": vol_1m["Rel 1Min Vol"],
            "Pre-Market %": premarket["Pre-Market %"],
            "Rel Volume": round(rel_volume, 2),
            "5D %": round(five_day_change, 2),
            "RSI": round(rsi, 1),
            "Volatility %": round(volatility, 1),
            "Bounce Score": round(bounce_score, 1),
            "Support": round(recent_support, 2),
            "Resistance": round(recent_resistance, 2),
            "Pivot": round(pivot, 2),
            "S1": round(s1, 2),
            "R1": round(r1, 2),
            "High Vol Level": round(high_vol_price, 2),
            "VWAP (10D)": round(vwap, 2),
            "SMA 20": round(sma_20, 2),
            "SMA 50": round(sma_50, 2),
            "Yahoo News": extra["Yahoo News"],
            "Google News": extra["Google News"],
            "Earnings Date": extra["Earnings Date"],
            "Short Interest %": extra["Short Interest %"],
            "Put/Call Ratio": extra["Put/Call Ratio"],
            "Sector": extra["Sector"]
        }
    except Exception as e:
        st.error(f"Error with {ticker}: {e}")
        return None

if analyze:
    with st.spinner("Fetching data..."):
        results = [get_stock_data(t) for t in tickers]
        results = [r for r in results if r]
        
        if not results:
            st.error("No data retrieved.")
            st.stop()
        
        df = pd.DataFrame(results)
        df = df.sort_values("Bounce Score", ascending=False).reset_index(drop=True)
        df["Rank"] = df.index + 1
        
        st.subheader("📰 News & Fundamentals")
        st.dataframe(
            df[["Ticker", "Yahoo News", "Google News", "Earnings Date", "Short Interest %", "Put/Call Ratio", "Sector"]],
            use_container_width=True
        )
        st.caption("**Short Interest %** = % of shares sold short | **Put/Call Ratio** > 1 = more puts (bearish sentiment)")
        
        st.subheader("📊 1-Minute Volume")
        st.dataframe(df[["Ticker", "1Min Vol", "Rel 1Min Vol"]], use_container_width=True)
        st.caption("**Rel 1Min Vol** = Latest 1-min volume ÷ average 1-min volume")
        
        st.subheader("📊 Main Comparison")
        st.dataframe(df[["Rank", "Ticker", "Price", "Day %", "Rel Volume", "5D %", "RSI", "Volatility %", "Bounce Score"]], use_container_width=True)
        
        winner = df.iloc[0]
        st.success(f"**Best Bounce Candidate: {winner['Ticker']}** | Bounce Score: {winner['Bounce Score']}")
        
        st.subheader("📍 Support / Resistance / Pivots")
        st.dataframe(df[["Ticker", "Price", "Support", "S1", "Pivot", "R1", "Resistance"]], use_container_width=True)
        
        st.subheader("📈 Moving Averages & Volume Levels")
        st.dataframe(df[["Ticker", "Price", "SMA 20", "SMA 50", "High Vol Level", "VWAP (10D)"]], use_container_width=True)
        
        st.caption(f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by yfinance")

else:
    st.info("Enter tickers on the left and click **Analyze Stocks**")
