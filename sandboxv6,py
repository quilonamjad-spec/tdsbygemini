import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.express as px

# --- SETTINGS ---
st.set_page_config(layout="wide")
st.markdown("""
<style>
    .card-buy { background-color: #151922; padding: 15px; border-radius: 10px; border-top: 5px solid #00c805; }
</style>
""", unsafe_allow_html=True)

# --- DATA FETCHING WITH CACHE ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_data(ticker_symbol):
    """Fetches data from Yahoo Finance and caches it for 5 minutes."""
    try:
        df = yf.Ticker(ticker_symbol).history(period="1d", interval="5m")
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame() # Return empty dataframe on error

# --- LOGIC FUNCTIONS ---
def analyze_pillar_3_patterns(df_slice, direction):
    if len(df_slice) < 3: return "Standard", 10
    c1, c2, c3 = df_slice.iloc[-1], df_slice.iloc[-2], df_slice.iloc[-3]
    is_green1, is_green2, is_green3 = c1['Close'] > c1['Open'], c2['Close'] > c2['Open'], c3['Close'] > c3['Open']
    if direction == "BUY":
        if is_green1 and is_green2 and is_green3: return "Three White Soldiers", 45
        if not is_green2 and is_green1: return "Bullish Engulfing", 40
        return "Standard Green", 30
    else:
        if not is_green1 and not is_green2 and not is_green3: return "Three Black Crows", 45
        if is_green2 and not is_green1: return "Bearish Engulfing", 40
        return "Standard Red", 30

def get_full_score(df_slice, direction):
    latest = df_slice.iloc[-1]
    ema9 = ta.trend.ema_indicator(df_slice['Close'], window=9).iloc[-1]
    ema_dist = ((latest['Close'] - ema9) / ema9) * 100
    score = 40 if abs(ema_dist) <= 0.3 else 25
    
    vol_mean = df_slice['Volume'].rolling(20).mean().iloc[-1]
    vol_std = df_slice['Volume'].rolling(20).std().iloc[-1]
    z_score = (latest['Volume'] - vol_mean) / vol_std if vol_std != 0 else 0
    score += 30 if z_score > 1.0 else (15 if z_score > 0 else 0)
    
    try:
        adx = ta.trend.ADXIndicator(df_slice['High'], df_slice['Low'], df_slice['Close'], window=14).adx().iloc[-1] if len(df_slice) > 14 else 0
    except: adx = 0
    score += 25 if adx > 22 else (10 if adx >= 18 else 0)
    
    rsi = ta.momentum.rsi(df_slice['Close'], window=14).iloc[-1]
    if direction == "BUY": score += 25 if 48 <= rsi <= 70 else (10 if 71 <= rsi <= 78 else 0)
    else: score += 25 if 30 <= rsi <= 52 else (10 if 22 <= rsi < 30 else 0)
    
    pattern, p_score = analyze_pillar_3_patterns(df_slice, direction)
    return score + p_score, pattern, rsi, ema_dist, z_score

# --- UI ---
st.title("🧪 Momentum Sandbox: Snapshot & Trend")
symbol = st.text_input("Enter Ticker", "RELIANCE.NS").upper()

if st.button("Analyze"):
    df = yf.Ticker(symbol).history(period="1d", interval="5m").between_time('09:30', '15:30')
    
    if df.empty:
        st.error("No intraday data found.")
    else:
        direction = "BUY" if df['Close'].iloc[-1] > ta.trend.ema_indicator(df['Close'], window=9).iloc[-1] else "SHORT"
        
        # Calculate Snapshot
        score, pattern, rsi, ema_d, vol_z = get_full_score(df, direction)
        
        col1, col2 = st.columns([1, 3])
       
            
                # Dynamically set the class based on direction
        card_class = "card-buy" if direction == "BUY" else "card-short"
        
        # Define the dynamic border color
        border_color = "#00c805" if direction == "BUY" else "#ff3b30"
        
        with col1:
            st.markdown(f"""
                <div class="{card_class}" style="border-top: 5px solid {border_color}; background-color: #151922; padding: 15px; border-radius: 10px;">
                    <div style="font-size:18px; font-weight:bold;">{symbol}</div>
                    <div style="font-size:24px; color:{border_color};">{score} PTS</div>
                    <div>{pattern}</div>
                    <hr style="border-color:#38435a;">
                    <div>EMA Dist: {ema_d:.2f}%</div>
                    <div>RSI: {rsi:.1f}</div>
                    <div>Vol Z: {vol_z:.2f}σ</div>
                </div>
                """, unsafe_allow_html=True)
         
        with col2:
            # Calculate Score History with Negative Multiplier for Shorts
            results = []
            for i in range(20, len(df)):
                s, _, _, _, _ = get_full_score(df.iloc[:i+1], direction)
                plot_score = s if direction == "BUY" else -s
                results.append({'Time': df.index[i], 'Score': plot_score})
            results = [{'Time': df.index[i], 'Score': get_full_score(df.iloc[:i+1], direction)[0]} for i in range(20, len(df))]
            fig = px.line(pd.DataFrame(results), x='Time', y='Score', title="Score Evolution")
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
