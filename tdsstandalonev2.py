import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import time
from datetime import datetime

# --- SETTINGS & CSS ---
st.set_page_config(layout="wide", page_title="Watchlist Sandbox")
st.markdown("""
<style>
    .card-buy { background-color: #151922; padding: 15px; border-radius: 10px; border-top: 5px solid #00c805; margin-bottom: 15px; }
    .card-short { background-color: #151922; padding: 15px; border-radius: 10px; border-top: 5px solid #ff3b30; margin-bottom: 15px; }
    .metric-row { display: flex; justify-content: space-between; font-size: 13px; color: #d1d4dc; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- CORE LOGIC ENGINE (Weights preserved from your criteria) ---
def analyze_pillar_3_patterns(df, direction):
    if len(df) < 3:
        latest = df.iloc[-1]
        is_bullish_day = latest['Close'] > latest['Open']
        if direction == "BUY":
            return "Standard", (30 if is_bullish_day else 10)
        else:
            return "Standard", (30 if not is_bullish_day else 10)

    c1 = df.iloc[-1]   # Today
    c2 = df.iloc[-2]   # Yesterday
    c3 = df.iloc[-3]   # 2 Days Ago

    body1 = abs(c1['Close'] - c1['Open'])
    body1 = 0.001 if body1 == 0 else body1
    
    is_green1 = c1['Close'] > c1['Open']
    is_green2 = c2['Close'] > c2['Open']
    is_green3 = c3['Close'] > c3['Open']

    lower_wick1 = min(c1['Open'], c1['Close']) - c1['Low']
    upper_wick1 = c1['High'] - max(c1['Open'], c1['Close'])

    if direction == "BUY":
        if is_green1 and is_green2 and is_green3:
            if c1['Close'] > c2['Close'] > c3['Close'] and c1['Open'] > c2['Open'] > c3['Open']:
                return "Three White Soldiers", 45
        if not is_green2 and is_green1:
            if c1['Close'] >= c2['Open'] and c1['Open'] <= c2['Close']:
                return "Bullish Engulfing", 40
        if lower_wick1 >= (2 * body1) and upper_wick1 <= (0.4 * body1):
            return "Hammer", 35
        return "Standard Green", (30 if is_green1 else 10)
    else:
        if not is_green1 and not is_green2 and not is_green3:
            if c1['Close'] < c2['Close'] < c3['Close'] and c1['Open'] < c2['Open'] < c3['Open']:
                return "Three Black Crows", 45
        if is_green2 and not is_green1:
            if c1['Close'] <= c2['Open'] and c1['Open'] >= c2['Close']:
                return "Bearish Engulfing", 40
        if upper_wick1 >= (2 * body1) and lower_wick1 <= (0.4 * body1):
            return "Shooting Star", 35
        return "Standard Red", (30 if not is_green1 else 10)

def get_score(latest, df, direction):
    score = 0
    # EMA Dist: 40 if <= 0.3%, 25 otherwise
    score += 40 if abs(latest['EMA_Dist']) <= 0.3 else 25
    # Vol Z: 30 if > 1.0, 15 if > 0
    score += 30 if latest['Vol_ZScore'] > 1.0 else (15 if latest['Vol_ZScore'] > 0 else 0)
    # ADX: 25 if > 22, 10 if >= 18
    score += 25 if latest['ADX'] > 22 else (10 if latest['ADX'] >= 18 else 0)
    # RSI: 25 if in zone, 10 if near zone
    if direction == "BUY":
        score += 25 if 48 <= latest['RSI'] <= 70 else (10 if 71 <= latest['RSI'] <= 78 else 0)
    else:
        score += 25 if 30 <= latest['RSI'] <= 52 else (10 if 22 <= latest['RSI'] < 30 else 0)
    
    pattern, p_score = analyze_pillar_3_patterns(df, direction)
    return score + p_score, pattern

# --- UI INTERFACE ---
st.title("🧪 Watchlist Sandbox Tester")
watchlist = st.sidebar.text_area("Enter Tickers (comma separated)", "RELIANCE.NS, TCS.NS, INFY.NS")
symbols = [s.strip().upper() for s in watchlist.split(",") if s.strip()]

if st.sidebar.button("Analyze Watchlist"):
    cols = st.columns(4) # 4 columns for grid layout
    for i, symbol in enumerate(symbols[:12]):
        with cols[i % 4]:
            try:
                df = yf.Ticker(symbol).history(period="60d", interval="1d")
                # Calculate metrics (same as your original logic)
                df['9_EMA'] = ta.trend.ema_indicator(df['Close'], window=9)
                df['EMA_Dist'] = ((df['Close'] - df['9_EMA']) / df['9_EMA']) * 100
                df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
                df['ADX'] = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14).adx()
                df['Vol_ZScore'] = (df['Volume'] - df['Volume'].rolling(20).mean()) / df['Volume'].rolling(20).std()
                
                latest = df.iloc[-1]
                direction = "BUY" if latest['Close'] > latest['9_EMA'] else "SHORT"
                score, pattern = get_score(latest, df, direction)
                
                style = "card-buy" if direction == "BUY" else "card-short"
                st.markdown(f"""
                <div class="{style}">
                    <div style="font-size:18px; font-weight:bold;">{symbol.replace('.NS', '')}</div>
                    <div style="font-size:20px; font-weight:bold; color:{'#00c805' if direction=='BUY' else '#ff3b30'};">{score} PTS</div>
                    <div style="font-size:11px; margin-bottom:10px;">{pattern}</div>
                    <div class="metric-row"><span>EMA Dist:</span><span>{latest['EMA_Dist']:.2f}%</span></div>
                    <div class="metric-row"><span>RSI:</span><span>{latest['RSI']:.1f}</span></div>
                    <div class="metric-row"><span>Vol Z:</span><span>{latest['Vol_ZScore']:.1f}σ</span></div>
                </div>
                """, unsafe_allow_html=True)
            except: st.error(f"Error: {symbol}")
