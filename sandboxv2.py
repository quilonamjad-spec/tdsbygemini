import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.express as px

# --- YOUR EXISTING PATTERN LOGIC ---
def analyze_pillar_3_patterns(df_slice, direction):
    # Ensure we have at least 3 candles to look back
    if len(df_slice) < 3: return "Standard", 10
    
    c1, c2, c3 = df_slice.iloc[-1], df_slice.iloc[-2], df_slice.iloc[-3]
    body1 = abs(c1['Close'] - c1['Open']) or 0.001
    is_green1, is_green2, is_green3 = c1['Close'] > c1['Open'], c2['Close'] > c2['Open'], c3['Close'] > c3['Open']
    
    if direction == "BUY":
        if is_green1 and is_green2 and is_green3: return "Three White Soldiers", 45
        if not is_green2 and is_green1: return "Bullish Engulfing", 40
        return "Standard Green", 30
    else:
        if not is_green1 and not is_green2 and not is_green3: return "Three Black Crows", 45
        if is_green2 and not is_green1: return "Bearish Engulfing", 40
        return "Standard Red", 30

# --- UPDATED SCORE CALCULATION ---
def get_full_score(df_slice, direction):
    latest = df_slice.iloc[-1]
    
    # 1. EMA Distance (40/25)
    ema9 = ta.trend.ema_indicator(df_slice['Close'], window=9).iloc[-1]
    ema_dist = ((latest['Close'] - ema9) / ema9) * 100
    score = 40 if abs(ema_dist) <= 0.3 else 25
    
    # 2. Volume Z-Score (30/15)
    vol_mean = df_slice['Volume'].rolling(20).mean().iloc[-1]
    vol_std = df_slice['Volume'].rolling(20).std().iloc[-1]
    z_score = (latest['Volume'] - vol_mean) / vol_std if vol_std != 0 else 0
    score += 30 if z_score > 1.0 else (15 if z_score > 0 else 0)
    
    # 3. ADX (25/10)
    adx = ta.trend.ADXIndicator(df_slice['High'], df_slice['Low'], df_slice['Close'], window=14).adx().iloc[-1]
    score += 25 if adx > 22 else (10 if adx >= 18 else 0)
    
    # 4. RSI (25/10)
    rsi = ta.momentum.rsi(df_slice['Close'], window=14).iloc[-1]
    if direction == "BUY":
        score += 25 if 48 <= rsi <= 70 else (10 if 71 <= rsi <= 78 else 0)
    else:
        score += 25 if 30 <= rsi <= 52 else (10 if 22 <= rsi < 30 else 0)
        
    # 5. Pattern Score
    _, p_score = analyze_pillar_3_patterns(df_slice, direction)
    
    return score + p_score

# --- UI & EXECUTION ---
st.title("📊 Integrated Momentum Sandbox")
symbol = st.text_input("Ticker", "RELIANCE.NS").upper()

if st.button("Generate Trend Graph"):
    df = yf.Ticker(symbol).history(period="1d", interval="5m")
    df = df.between_time('09:30', '15:30')
    
    results = []
    direction = "BUY" if df['Close'].iloc[-1] > ta.trend.ema_indicator(df['Close'], window=9).iloc[-1] else "SHORT"
    
    for i in range(20, len(df)):
        score = get_full_score(df.iloc[:i+1], direction)
        results.append({'Time': df.index[i], 'Score': score})
    
    fig = px.line(pd.DataFrame(results), x='Time', y='Score', title=f"Full Criteria Score: {symbol}")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig)