import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import plotly.express as px

# --- SETTINGS ---
st.set_page_config(layout="wide", page_title="Momentum Sandbox Engine")

st.markdown("""
<style>
    .card-container {
        padding: 20px; 
        border-radius: 10px; 
        background-color: #151922;
        border: 1px solid #2d3139;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        margin: 8px 0;
        font-size: 14px;
        color: #cfd6e4;
    }
    .metric-value {
        font-weight: bold;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# --- ENGINE: ROBUST DATA FETCHING ---
@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday_data(ticker_symbol):
    """
    Fetches 5 days of history to ensure indicators (RSI 14, Vol Z-Score 20) 
    have a rolling cushion and do not return NaN during early market hours.
    """
    try:
        df = yf.Ticker(ticker_symbol).history(period="5d", interval="5m")
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df
    except Exception as e:
        st.error(f"Error fetching telemetry for {ticker_symbol}: {e}")
        return pd.DataFrame()

# --- ENGINE: QUANT MATHEMATICS STACK ---
def analyze_pillar_3_patterns(df_slice, direction):
    if len(df_slice) < 3: 
        return "Standard", 10
    c1, c2, c3 = df_slice.iloc[-1], df_slice.iloc[-2], df_slice.iloc[-3]
    is_green1 = c1['Close'] > c1['Open']
    is_green2 = c2['Close'] > c2['Open']
    is_green3 = c3['Close'] > c3['Open']
    
    if direction == "BUY":
        if is_green1 and is_green2 and is_green3: return "Three White Soldiers", 35
        if not is_green2 and is_green1: return "Bullish Engulfing", 25
        return "Standard Green", 20
    else:
        if not is_green1 and not is_green2 and not is_green3: return "Three Black Crows", 35
        if is_green2 and not is_green1: return "Bearish Engulfing", 25
        return "Standard Red", 20

def get_full_score(df_slice, direction):
    latest = df_slice.iloc[-1]
    
    # 1. 9 EMA Distance Score
    ema9 = ta.trend.ema_indicator(df_slice['Close'], window=9).iloc[-1]
    ema_dist = ((latest['Close'] - ema9) / ema9) * 100
    score = 30 if abs(ema_dist) <= 0.3 else 20
    
    # 2. Volume Shock Z-Score
    vol_mean = df_slice['Volume'].rolling(20).mean().iloc[-1]
    vol_std = df_slice['Volume'].rolling(20).std().iloc[-1]
    z_score = (latest['Volume'] - vol_mean) / vol_std if vol_std != 0 else 0
    score += 30 if z_score > 1.0 else (15 if z_score > 0 else 0)
    
    # 3. ADX Structural Strength Score
    try:
        adx = ta.trend.ADXIndicator(df_slice['High'], df_slice['Low'], df_slice['Close'], window=14).adx().iloc[-1] if len(df_slice) > 14 else 0
    except: 
        adx = 0
    score += 25 if adx > 22 else (10 if adx >= 18 else 0)
    
    # 4. RSI Boundary Core
    rsi = ta.momentum.rsi(df_slice['Close'], window=14).iloc[-1]
    if direction == "BUY": 
        score += 25 if 48 <= rsi <= 70 else (10 if 71 <= rsi <= 78 else 0)
    else: 
        score += 25 if 30 <= rsi <= 52 else (10 if 22 <= rsi < 30 else 0)
    
    # 5. Candlestick Formations
    pattern, p_score = analyze_pillar_3_patterns(df_slice, direction)
    return score + p_score, pattern, rsi, ema_dist, z_score

# --- USER INTERFACE DISPLAY ---
st.title("🧪 Momentum Sandbox: Production Model")
st.markdown("Uses deep historical tracking to prevent early-morning calculation drops.")

symbol = st.text_input("Enter Market Ticker Symbol:", "RELIANCE.NS").upper()

if st.button("Execute Strategic Analysis", use_container_width=True):
    raw_df = fetch_intraday_data(symbol)
    
    if raw_df.empty or len(raw_df) < 25:
        st.error("Engine failure: Minimal back-history criteria not met for this asset.")
    else:
        # Isolate exactly today's subset loop parameters
        latest_date = raw_df.index.date[-1]
        today_df = raw_df[raw_df.index.date == latest_date]
        start_idx = len(raw_df) - len(today_df)
        
        # Calculate Current Real-time Snapshot Status
        current_ema = ta.trend.ema_indicator(raw_df['Close'], window=9).iloc[-1]
        direction = "BUY" if raw_df['Close'].iloc[-1] > current_ema else "SHORT"
        score, pattern, rsi, ema_d, vol_z = get_full_score(raw_df, direction)
        
        border_color = "#00c805" if direction == "BUY" else "#ff3b30"
        
        layout_left, layout_right = st.columns([1, 2.5])
        
        # COLUMN 1: Real-Time Tactical Profile Card
        with layout_left:
            st.markdown(f"""
            <div class="card-container" style="border-top: 5px solid {border_color};">
                <div style="font-size: 14px; color: #848e9c; font-weight: bold; text-transform: uppercase;">Live Engine Status</div>
                <div style="font-size: 26px; font-weight: bold; margin-bottom: 5px;">{symbol}</div>
                <div style="font-size: 32px; color: {border_color}; font-weight: 800; margin-bottom: 2px;">{score} PTS</div>
                <div style="font-size: 14px; font-weight: bold; color: #a4b0c6; margin-bottom: 15px;">⚡ {pattern}</div>
                <hr style="border-color: #2d3139; margin: 10px 0;">
                <div class="metric-row"><span>Bias Execution:</span><span class="metric-value" style="color: {border_color};">{direction}</span></div>
                <div class="metric-row"><span>EMA 9 Distance:</span><span class="metric-value">{ema_d:.2f}%</span></div>
                <div class="metric-row"><span>Relative Strength (RSI):</span><span class="metric-value">{rsi:.1f}</span></div>
                <div class="metric-row"><span>Volume Z-Score:</span><span class="metric-value">{vol_z:.2f}σ</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        # COLUMN 2: Continuous Historical Score Progress Flow Chart
        with layout_right:
            results = []
            
            # Historical slice progression scanning engine
            for i in range(start_idx, len(raw_df)):
                df_slice = raw_df.iloc[:i+1]
                slice_ema = ta.trend.ema_indicator(df_slice['Close'], window=9).iloc[-1]
                current_direction = "BUY" if df_slice['Close'].iloc[-1] > slice_ema else "SHORT"
                
                s, _, _, _, _ = get_full_score(df_slice, current_direction)
                plot_score = s if current_direction == "BUY" else -s
                results.append(plot_score)
            
            # Build and smooth the tracking frame
            score_df = pd.DataFrame({'Score': results}, index=today_df.index)
            score_df['Smoothed_Score'] = score_df['Score'].rolling(window=3).mean()
            
            # Limit charting scope cleanly to standard active tracking hours
            score_df = score_df.between_time('09:15', '15:30')
            
            # Plotly Visualization Layout Configuration
            fig = px.line(
                score_df, 
                x=score_df.index, 
                y='Smoothed_Score', 
                title="Momentum Score Curve (3-Period Smoothed Evolution)"
            )
            
            fig.add_hline(y=0, line_dash="dash", line_color="#5c6370", annotation_text="Bias Boundary Line")
            fig.update_traces(line_color=border_color, line_width=3)
            fig.update_layout(
                template="plotly_dark", 
                xaxis_title="Timeline Feed", 
                yaxis_title="Smoothed Momentum Scale",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            
            st.plotly_chart(fig, use_container_width=True)
