import streamlit as tf  # Custom safe shorthand alias
import yfinance as yf
import pandas as pd
import ta
import time
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Set page configuration to wide layout
tf.set_page_config(page_title="Decision Scanner Dashboard", layout="wide")

# Custom CSS injection for dark-themed trading cards
tf.markdown("""
<style>
    .reportview-container { background: #0E1117; }
    .card-container-buy {
        background-color: #151922;
        border-radius: 10px;
        padding: 15px;
        border-top: 5px solid #00c805;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .card-container-short {
        background-color: #151922;
        border-radius: 10px;
        padding: 15px;
        border-top: 5px solid #ff3b30;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.3);
    }
    .ticker-title { font-size: 20px; font-weight: bold; color: #ffffff; margin-bottom: 2px; }
    .rank-badge { font-size: 12px; color: #8a99ad; font-weight: 600; text-transform: uppercase; }
    .score-badge { background-color: #1e2433; padding: 4px 8px; border-radius: 5px; font-weight: bold; font-size: 14px; text-align: center; margin: 8px 0px; }
    .metric-row { display: flex; justify-content: space-between; margin-top: 6px; font-size: 13px; color: #d1d4dc; }
    .metric-val { font-weight: bold; color: #ffffff; }
    /* Style adjustment to make the chart launch button look seamless */
    div.stPopover > button {
        width: 100%;
        background-color: #1e2433 !important;
        color: #ffffff !important;
        border: 1px solid #38435a !important;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
tf.sidebar.header("⚙️ SCANNER CONTROLS")
target_date = tf.sidebar.date_input("Analysis Date", datetime.today())
is_historical = target_date < datetime.today().date()

if is_historical:
    tf.sidebar.warning(f"🕒 Time Machine Active: Analyzing market state as of EOD {target_date.strftime('%d-%b-%Y')}")
else:
    tf.sidebar.success("⚡ Live Market Mode Active")

@tf.cache_data(ttl=3600)
def get_nifty_500_tickers():
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        df = pd.read_csv(url)
        return [f"{sym}.NS" for sym in df['Symbol'].tolist()]
    except Exception:
        return ["RELIANCE.NS", "SUNPHARMA.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]

def calculate_metrics(df):
    if len(df) < 35: return None
    close = df['Close']
    volume = df['Volume']
    df['9_EMA'] = ta.trend.ema_indicator(close, window=9)
    df['EMA_Dist'] = ((close - df['9_EMA']) / df['9_EMA']) * 100
    macd_obj = ta.trend.MACD(close)
    df['MACD_Line'] = macd_obj.macd()
    df['MACD_Signal'] = macd_obj.macd_signal()
    df['MACD_Diff'] = macd_obj.macd_diff()
    df['RSI'] = ta.momentum.rsi(close, window=14)
    df['ADX'] = ta.trend.ADXIndicator(df['High'], df['Low'], close, window=14).adx()
    df['Vol_Mean'] = volume.rolling(window=20).mean()
    df['Vol_Std'] = volume.rolling(window=20).std()
    df['Vol_ZScore'] = (volume - df['Vol_Mean']) / df['Vol_Std']
    return df

def process_and_score_stock(symbol, selected_date):
    try:
        ticker = yf.Ticker(symbol)
        if is_historical:
            start_date = (selected_date - timedelta(days=100)).strftime('%Y-%m-%d')
            end_date = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
            df = ticker.history(start=start_date, end=end_date, interval="1d")
        else:
            df = ticker.history(period="60d", interval="1d")
            
        df = calculate_metrics(df)
        if df is None or df.empty: return None
            
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        ema_dist = latest['EMA_Dist']
        z_score = latest['Vol_ZScore']
        adx = latest['ADX']
        rsi = latest['RSI']
        is_bull_candle = latest['Close'] > latest['Open']
        
        # --- FETCH INTRADAY 5-MINUTE DATA FOR POP-UP ---
        try:
            start_5m = selected_date.strftime('%Y-%m-%d')
            end_5m = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
            df_5m = ticker.history(start=start_5m, end=end_5m, interval="5m")
            if not df_5m.empty:
                df_5m['9_EMA'] = ta.trend.ema_indicator(df_5m['Close'], window=9)
        except Exception:
            df_5m = pd.DataFrame()
        
        # BUY SIGNALS
        is_up_phase = latest['MACD_Line'] > latest['MACD_Signal'] or latest['MACD_Diff'] > prev['MACD_Diff']
        if is_up_phase and (0 <= ema_dist <= 1.0):
            score = 0
            score += 40 if ema_dist <= 0.25 else 25
            score += 30 if z_score > 1.0 else (15 if z_score > 0 else 0)
            score += 25 if adx > 25 else (10 if adx >= 20 else 0)
            score += 25 if 50 <= rsi <= 68 else (10 if 69 <= rsi <= 75 else 0)
            score += 30 if is_bull_candle else 10
            return {"Ticker": symbol.replace(".NS", ""), "Direction": "BUY", "Score": score, 
                    "EMA_Dist": round(ema_dist, 2), "Vol_Z": round(z_score, 1), "RSI": round(rsi, 1), 
                    "ADX": round(adx, 1), "df_5m": df_5m}

        # SHORT SIGNALS
        is_down_phase = latest['MACD_Line'] < latest['MACD_Signal'] or latest['MACD_Diff'] < prev['MACD_Diff']
        if is_down_phase and (-1.0 <= ema_dist <= 0):
            score = 0
            abs_dist = abs(ema_dist)
            score += 40 if abs_dist <= 0.25 else 25
            score += 30 if z_score > 1.0 else (15 if z_score > 0 else 0)
            score += 25 if adx > 25 else (10 if adx >= 20 else 0)
            score += 25 if 32 <= rsi <= 50 else (10 if 25 <= rsi < 32 else 0)
            score += 30 if not is_bull_candle else 10
            return {"Ticker": symbol.replace(".NS", ""), "Direction": "SHORT", "Score": score, 
                    "EMA_Dist": round(ema_dist, 2), "Vol_Z": round(z_score, 1), "RSI": round(rsi, 1), 
                    "ADX": round(adx, 1), "df_5m": df_5m}
        return None
    except Exception:
        return None

# --- DASHBOARD HEADER ---
tf.title("🎯 NIFTY 500 DECISION SCANNER")
tf.subheader(f"Real-time Funnel Filtering & Multi-Directional Ranking ({target_date.strftime('%d-%b-%Y')})")

if tf.button("🚀 Execute Market Scan", use_container_width=True):
    symbols = get_nifty_500_tickers()
    all_opportunities = []
    
    progress_bar = tf.progress(0)
    status_text = tf.empty()
    
    for idx, symbol in enumerate(symbols):
        res = process_and_score_stock(symbol, target_date)
        if res: all_opportunities.append(res)
        if idx % 25 == 0:
            pct = int((idx / len(symbols)) * 100)
            progress_bar.progress(pct)
            status_text.text(f"Processing data streams: Analyzing {idx}/500 tickers...")
        time.sleep(0.01)
        
    progress_bar.empty()
    status_text.empty()

    if all_opportunities:
        df_master = pd.DataFrame(all_opportunities)
        buys_df = df_master[df_master['Direction'] == "BUY"].sort_values(by="Score", ascending=False).head(5)
        shorts_df = df_master[df_master['Direction'] == "SHORT"].sort_values(by="Score", ascending=False).head(5)
        
        # ----------------------------------------------------
        # ROW 1: LONG OPPORTUNITIES (BUYS)
        # ----------------------------------------------------
        tf.markdown("### 🔥 TOP BULLISH ACCELERATIONS (BUYS)")
        if not buys_df.empty:
            cols = tf.columns(5)
            for i, (_, row) in enumerate(buys_df.iterrows()):
                with cols[i]:
                    tf.markdown(f"""
                    <div class="card-container-buy">
                        <div class="rank-badge">RANK #{i+1} • LONG</div>
                        <div class="ticker-title">{row['Ticker']}</div>
                        <div class="score-badge" style="color: #00c805;">{int(row['Score'])} / 150 PTS</div>
                        <div class="metric-row"><span>9 EMA Dist:</span><span class="metric-val">{row['EMA_Dist']}%</span></div>
                        <div class="metric-row"><span>Vol Z-Score:</span><span class="metric-val">{row['Vol_Z']}σ</span></div>
                        <div class="metric-row"><span>RSI (14):</span><span class="metric-val">{row['RSI']}</span></div>
                        <div class="metric-row"><span>ADX Trend:</span><span class="metric-val">{row['ADX']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Candlestick Popover
                    with tf.popover("🕯️ View 5-Min Candles"):
                        tf.write(f"### {row['Ticker']} Intraday Structure")
                        df_intraday = row['df_5m']
                        
                        if (df_intraday is not None) and (not df_intraday.empty):
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(
                                x=df_intraday.index, open=df_intraday['Open'], high=df_intraday['High'],
                                low=df_intraday['Low'], close=df_intraday['Close'], name="5m Candles"
                            ))
                            fig.add_trace(go.Scatter(
                                x=df_intraday.index, y=df_intraday['9_EMA'], mode='lines', 
                                line=dict(color='#00d2ff', width=1.5), name='9 EMA'
                            ))
                            fig.update_layout(
                                template="plotly_dark", xaxis_rangeslider_visible=False,
                                margin=dict(l=10, r=10, t=10, b=10), height=300
                            )
                            tf.plotly_chart(fig, use_container_width=True)
                        else:
                            tf.error("5m intraday data unavailable for this date. (Max history limit: 60 days)")
        else:
            tf.info("No high-probability long configurations detected across the universe for this date.")

        tf.markdown("---")

        # ----------------------------------------------------
        # ROW 2: SHORT OPPORTUNITIES (SHORTS)
        # ----------------------------------------------------
        tf.markdown("### 💀 TOP BEARISH BREAKDOWNS (SHORTS)")
        if not shorts_df.empty:
            cols = tf.columns(5)
            for i, (_, row) in enumerate(shorts_df.iterrows()):
                with cols[i]:
                    tf.markdown(f"""
                    <div class="card-container-short">
                        <div class="rank-badge">RANK #{i+1} • SHORT</div>
                        <div class="ticker-title">{row['Ticker']}</div>
                        <div class="score-badge" style="color: #ff3b30;">{int(row['Score'])} / 150 PTS</div>
                        <div class="metric-row"><span>9 EMA Dist:</span><span class="metric-val">{row['EMA_Dist']}%</span></div>
                        <div class="metric-row"><span>Vol Z-Score:</span><span class="metric-val">{row['Vol_Z']}σ</span></div>
                        <div class="metric-row"><span>RSI (14):</span><span class="metric-val">{row['RSI']}</span></div>
                        <div class="metric-row"><span>ADX Trend:</span><span class="metric-val">{row['ADX']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Candlestick Popover
                    with tf.popover("🕯️ View 5-Min Candles"):
                        tf.write(f"### {row['Ticker']} Intraday Structure")
                        df_intraday = row['df_5m']
                        
                        if (df_intraday is not None) and (not df_intraday.empty):
                            fig = go.Figure()
                            fig.add_trace(go.Candlestick(
                                x=df_intraday.index, open=df_intraday['Open'], high=df_intraday['High'],
                                low=df_intraday['Low'], close=df_intraday['Close'], name="5m Candles"
                            ))
                            fig.add_trace(go.Scatter(
                                x=df_intraday.index, y=df_intraday['9_EMA'], mode='lines', 
                                line=dict(color='#00d2ff', width=1.5), name='9 EMA'
                            ))
                            fig.update_layout(
                                template="plotly_dark", xaxis_rangeslider_visible=False,
                                margin=dict(l=10, r=10, t=10, b=10), height=300
                            )
                            tf.plotly_chart(fig, use_container_width=True)
                        else:
                            tf.error("5m intraday data unavailable for this date. (Max history limit: 60 days)")
        else:
            tf.info("No high-probability short configurations detected across the universe for this date.")
    else:
        tf.warning("The funnel excluded all Nifty 500 assets based on the structural criteria for this target.")
