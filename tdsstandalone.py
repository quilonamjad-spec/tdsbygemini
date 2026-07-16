import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.graph_objects as go
from datetime import datetime

# --- REUSE YOUR EXISTING LOGIC ---
# (Include your 'calculate_metrics' and 'analyze_pillar_3_patterns' functions here)
# [I have kept the structure clean below for you to paste them in]

def calculate_metrics(df):
    if len(df) < 35: return None
    close = df['Close']
    volume = df['Volume']
    df['9_EMA'] = ta.trend.ema_indicator(close, window=9)
    df['EMA_Dist'] = ((close - df['9_EMA']) / df['9_EMA']) * 100
    macd = ta.trend.MACD(close)
    df['MACD_Line'], df['MACD_Signal'] = macd.macd(), macd.macd_signal()
    df['RSI'] = ta.momentum.rsi(close, window=14)
    df['ADX'] = ta.trend.ADXIndicator(df['High'], df['Low'], close, window=14).adx()
    df['Vol_ZScore'] = (volume - volume.rolling(20).mean()) / volume.rolling(20).std()
    return df

# --- UI SETTINGS ---
st.set_page_config(layout="wide")
st.title("🧪 Watchlist Sandbox Tester")

# Sidebar Input
watchlist_input = st.sidebar.text_area("Enter Tickers (comma separated)", "RELIANCE.NS, TCS.NS, INFY.NS")
symbols = [s.strip().upper() for s in watchlist_input.split(",")]

if st.sidebar.button("Analyze Watchlist"):
    cols = st.columns(4) # 3 rows x 4 cols = 12 boxes
    
    for i, symbol in enumerate(symbols[:12]): # Limit to 12
        with cols[i % 4]:
            with st.spinner(f"Analyzing {symbol}..."):
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="60d", interval="1d")
                df = calculate_metrics(df)
                
                if df is not None:
                    latest = df.iloc[-1]
                    # Simple Scoring Logic (reusing your existing weights)
                    score = 0
                    score += 40 if abs(latest['EMA_Dist']) <= 0.3 else 25
                    score += 30 if latest['Vol_ZScore'] > 1.0 else 0
                    score += 25 if 48 <= latest['RSI'] <= 70 else 0
                    score += 25 if latest['ADX'] > 22 else 0
                    
                    color = "#00c805" if latest['Close'] > latest['9_EMA'] else "#ff3b30"
                    
                    st.markdown(f"""
                    <div style="background:#151922; padding:15px; border-radius:10px; border-top:5px solid {color}; margin-bottom:15px;">
                        <div style="font-size:18px; font-weight:bold;">{symbol}</div>
                        <div style="font-size:24px; font-weight:bold; color:{color};">{int(score)} PTS</div>
                        <div style="font-size:12px;">EMA Dist: {latest['EMA_Dist']:.2f}%</div>
                        <div style="font-size:12px;">RSI: {latest['RSI']:.1f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"Could not load {symbol}")
