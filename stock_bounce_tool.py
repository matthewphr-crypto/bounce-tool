import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Daily Stock Bounce Comparator", layout="wide")

st.title("📈 Daily Stock Bounce Comparator")
st.caption("Yahoo News • Google News • Earnings • Short Interest • Options • Sector • 1-Min Volume • Pre-Market • Technicals")

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
        pre_change_pct = info.get("preMarketChangePercent")
        pre_price = info.get("preMarketPrice")
        
        if pre_change_pct is not None:
            return {
                "Pre-Market Price": round(pre_price, 2) if pre_price else None,
                "Pre-Market %": round(pre_change_pct, 2)
            }
        
        regular_price = info.get("regularMarketPreviousClose") or info.get("previousClose")
        if pre_price and regular_price and regular_price != 0:
            change_pct = ((pre_price - regular_price) / regular_price) * 100
            return {
                "Pre-Market Price": round(pre_price, 2),
                "Pre-Market %": round(change_pct, 2)
            }
    except:
        pass
    return {"Pre-Market Price": None, "Pre-Market %": None}

def get_1min_volume(ticker):
    try:
        hist_1m = yf.Ticker(ticker).history(period="1d", interval="1m")
        if hist_1m.empty:
            return {"1Min Vol": None, "Rel 1Min Vol": None}
        latest = hist_1m['Volume'].iloc[-1]
        avg = hist_1m['Volume'].mean()
        return {
            "1Min Vol": int(latest),
            "Rel 1Min Vol": round(latest / avg, 2) if avg > 0 else 0
        }
    except:
        return {"1Min Vol": None, "Rel 1Min Vol": None}

def get_5min_levels(ticker):
    """Get Support/Resistance from recent 5-minute data"""
    try:
        # Last 5 days of 5-minute data
        hist_5m = yf.Ticker(ticker).history(period="5d", interval="5m")
        if hist_5m.empty or len(hist_5m) < 10:
            return {"Support (5m)": None, "Resistance (5m)": None}
        
        # Recent support/resistance from last ~2 sessions of 5m bars
        recent = hist_5m.tail(100)  # last ~100 five-minute bars
        support = recent['Low'].min()
        resistance = recent['High'].max()
        
        return {
            "Support (5m)": round(support, 2),
            "Resistance (5m)": round(resistance, 2)
        }
    except:
        return {"Support (5m)": None, "Resistance (5m)": None}

def get_extra_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        
        yahoo_news = "No recent news"
        try:
            news = getattr(stock, 'news', []) or []
            if news:
                titles = [n.get('title', '')[:55] for n in news[:2] if n.get('title')]
                if titles:
                    yahoo_news = " | ".join(titles)
        except:
            pass
        
        news_link = f"https://www.google.com/search?q={ticker}+stock+news&tbm=nws"
        
        earnings = info.get("earningsTimestamp") or info.get("earningsDate")
        earnings_date = "N/A"
        if earnings:
            try:
                if isinstance(earnings, (int, float)):
                    earnings_date = datetime.fromtimestamp(earnings).strftime("%Y-%m-%d")
                elif isinstance(earnings, list) and earnings:
                    earnings_date = str(earnings[0])[:10]
            except:
                pass
        
        short_pct = info.get("shortPercentOfFloat")
        short_interest = f"{short_pct*100:.1f}%" if short_pct else "N/A"
        
        pc_ratio = "N/A"
        try:
            options = stock.option_chain()
            if options and not options.calls.empty and not options.puts.empty:
                calls = options.calls['volume'].sum()
                puts = options.puts['volume'].sum()
                if calls > 0:
                    pc_ratio = round(puts / calls, 2)
        except:
            pass
        
        sector = info.get("sector") or "N/A"
        
        return {
            "Yahoo News": yahoo_news,
            "Google News": news_link,
            "Earnings Date": earnings_date,
            "Short Interest %": short_interest,
            "Put/Call Ratio": pc_ratio,
            "Sector": sector
        }
    except Exception:
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
        if hist.empty or len(hist) < 20:
            return None
        
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        day_change = ((current_price - prev_close) / prev_close) * 100
        
        premarket = get_premarket_data(ticker)
        vol_1m = get_1min_volume(ticker)
        levels_5m = get_5min_levels(ticker)
        extra = get_extra_data(ticker)
        
        today_volume = hist['Volume'].iloc[-1]
        avg_volume_20 = hist['Volume'].tail(20).mean()
        rel_volume = today_volume / avg_volume_20 if avg_volume_20 > 0 else 0
        
        five_day_change = ((current_price - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100 if len(hist) > 5 else 0
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.tail(10).std() * np.sqrt(252) * 100 if len(returns) >= 10 else 0
        rsi = calculate_rsi(hist['Close'], period=14)
        
        high_20 = hist['High'].tail(20).max()
        distance_from_high = ((high_20 - current_price) / high_20) * 100
        oversold_score = min(100, max(0, (abs(min(day_change, 0)) * 3) + (distance_from_high * 0.8) + (rel_volume * 8)))
        
        bounce_score = (rel_volume * 25) + (abs(min(day_change, 0)) * 4) + (oversold_score * 0.4) + (max(0, -five_day_change) * 1.5)
        
        # Daily pivots (still useful)
        prev_high = hist['High'].iloc[-2]
        prev_low = hist['Low'].iloc[-2]
        prev_close_pp = hist['Close'].iloc[-2]
        pivot = (prev_high + prev_low + prev_close_pp) / 3
        r1 = (2 * pivot) - prev_low
        s1 = (2 * pivot) - prev_high
        
        # Volume levels
        recent_hist = hist.tail(15)
        high_vol_price = recent_hist.loc[recent_hist['Volume'].idxmax(), 'Close']
        recent_10 = hist.tail(10)
        vwap = (recent_10['Close'] * recent_10['Volume']).sum() / recent_10['Volume'].sum()
        
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
        
        return {
            "Ticker": ticker,
            "Price": round(current_price, 2),
            "Day %": round(day_change, 2),
            "Pre-Market %": premarket["Pre-Market %"],
            "1Min Vol": vol_1m["1Min Vol"],
            "Rel 1Min Vol": vol_1m["Rel 1Min Vol"],
            "Rel Volume": round(rel_volume, 2),
            "5D %": round(five_day_change, 2),
            "RSI": round(rsi, 1) if pd.notna(rsi) else None,
            "Volatility %": round(volatility, 1),
            "Bounce Score": round(bounce_score, 1),
            "Support (5m)": levels_5m["Support (5m)"],
            "Resistance (5m)": levels_5m["Resistance (5m)"],
            "Pivot": round(pivot, 2),
            "S1": round(s1, 2),
            "R1": round(r1, 2),
            "High Vol Level": round(high_vol_price, 2),
            "VWAP (10D)": round(vwap, 2),
            "SMA 20": round(sma_20, 2) if pd.notna(sma_20) else None,
            "SMA 50": round(sma_50, 2) if sma_50 and pd.notna(sma_50) else None,
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
            column_config={
                "Google News": st.column_config.LinkColumn("Google News", display_text="Open")
            },
            use_container_width=True
        )
        
        st.subheader("📊 1-Minute Volume")
        st.dataframe(df[["Ticker", "1Min Vol", "Rel 1Min Vol"]], use_container_width=True)
        
        st.subheader("📊 Main Comparison")
        st.dataframe(df[["Rank", "Ticker", "Price", "Day %", "Pre-Market %", "Rel Volume", "5D %", "RSI", "Volatility %", "Bounce Score"]], use_container_width=True)
        
        winner = df.iloc[0]
        st.success(f"**Best Bounce Candidate: {winner['Ticker']}** | Bounce Score: {winner['Bounce Score']}")
        
        st.subheader("📍 Support / Resistance (5-minute data)")
        st.dataframe(df[["Ticker", "Price", "Support (5m)", "Resistance (5m)", "S1", "Pivot", "R1"]], use_container_width=True)
        st.caption("Support (5m) / Resistance (5m) = lowest low / highest high from recent 5-minute bars (last ~2 sessions).")
        
        st.subheader("📈 Moving Averages & Volume Levels")
        st.dataframe(df[["Ticker", "Price", "SMA 20", "SMA 50", "High Vol Level", "VWAP (10D)"]], use_container_width=True)
        
        st.caption(f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M')} | Powered by yfinance")

else:
    st.info("Enter tickers on the left and click **Analyze Stocks**")
