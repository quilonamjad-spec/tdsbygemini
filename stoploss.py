import streamlit as st
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime, timedelta, time

st.set_page_config(page_title="Standalone Trade Calculator", layout="centered")

st.markdown("""
<style>
    .metric-box { background-color: #151922; padding: 20px; border-radius: 10px; margin-top: 10px; border: 1px solid #38435a;}
    .buy-box { border-top: 5px solid #00c805; }
    .short-box { border-top: 5px solid #ff3b30; }
    .val { font-size: 20px; font-weight: bold; color: #ffffff; }
    .lbl { font-size: 14px; color: #8a99ad; margin-bottom: 5px;}
</style>
""", unsafe_allow_html=True)

st.title("🎯 Dynamic Trade & Risk Calculator")
st.write("Enter an exact time and ticker to calculate volatility-adjusted stop losses and targets (1:1.5 R:R).")

# --- USER INPUTS ---
col1, col2, col3 = st.columns(3)
with col1:
    symbol = st.text_input("Ticker Symbol", value="RELIANCE.NS").upper()
with col2:
    trade_date = st.date_input("Trade Date", value=datetime.today())
with col3:
    trade_time = st.time_input("Entry Time (HH:MM)", value=time(10, 15))

if st.button("Calculate Trade Levels", use_container_width=True):
    with st.spinner(f"Fetching historical volatility and exact time data for {symbol}..."):
        try:
            ticker = yf.Ticker(symbol)
            
            # 1. Fetch Daily Data to calculate the 14-day ATR
            # We pull 30 days to ensure we have enough data for the 14-day window
            start_daily = (trade_date - timedelta(days=30)).strftime('%Y-%m-%d')
            end_daily = (trade_date + timedelta(days=1)).strftime('%Y-%m-%d')
            df_daily = ticker.history(start=start_daily, end=end_daily, interval="1d")
            
            if len(df_daily) < 15:
                st.error("Not enough daily data to calculate ATR. Try a different ticker.")
                st.stop()
                
            df_daily['ATR'] = ta.volatility.average_true_range(df_daily['High'], df_daily['Low'], df_daily['Close'], window=14)
            current_atr = df_daily['ATR'].iloc[-1]  # Get the ATR for the selected trade day
            
            # 2. Fetch Intraday Data to find the exact entry price
            # 5-minute data is available for the last 60 days on Yahoo Finance
            start_intra = trade_date.strftime('%Y-%m-%d')
            end_intra = (trade_date + timedelta(days=1)).strftime('%Y-%m-%d')
            df_intra = ticker.history(start=start_intra, end=end_intra, interval="5m")
            
            if df_intra.empty:
                st.error("Intraday data not available for this date. (Yahoo Finance limit: 60 days max historical 5m data).")
                st.stop()
                
            # Create a simple time string column to bypass complex timezone matching
            df_intra['Time_Str'] = df_intra.index.strftime("%H:%M")
            target_time_str = trade_time.strftime("%H:%M")
            
            # Find the closest 5-minute candle at or immediately after the requested time
            matched_rows = df_intra[df_intra['Time_Str'] >= target_time_str]
            
            if not matched_rows.empty:
                exact_entry_time = matched_rows.iloc[0]['Time_Str']
                entry_price = matched_rows.iloc[0]['Close']
            else:
                # If time is past market hours, grab the last close of the day
                exact_entry_time = df_intra.iloc[-1]['Time_Str']
                entry_price = df_intra.iloc[-1]['Close']

            # 3. Apply the Risk/Reward Math
            long_stop = entry_price - current_atr
            long_target = entry_price + (current_atr * 1.5)
            
            short_stop = entry_price + current_atr
            short_target = entry_price - (current_atr * 1.5)

            # --- DISPLAY RESULTS ---
            st.success(f"Successfully locked data for **{symbol}** at **{exact_entry_time}** on **{trade_date.strftime('%d-%b-%Y')}**.")
            
            st.markdown(f"**Daily Volatility (14-ATR):** ₹{current_atr:.2f} *(This is how much the stock naturally breathes)*")
            st.markdown(f"**Exact Entry Price:** ₹{entry_price:.2f}")
            
            col_buy, col_short = st.columns(2)
            
            with col_buy:
                st.markdown(f"""
                <div class="metric-box buy-box">
                    <h3 style="margin-top: 0px; color: #00c805;">LONG SETUP (BUY)</h3>
                    <div class="lbl">Target (+1.5R):</div>
                    <div class="val" style="color: #00c805;">₹{long_target:.2f}</div>
                    <hr style="border-color: #38435a;">
                    <div class="lbl">Entry Price:</div>
                    <div class="val">₹{entry_price:.2f}</div>
                    <hr style="border-color: #38435a;">
                    <div class="lbl">Stop Loss (-1.0R):</div>
                    <div class="val" style="color: #ff3b30;">₹{long_stop:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col_short:
                st.markdown(f"""
                <div class="metric-box short-box">
                    <h3 style="margin-top: 0px; color: #ff3b30;">SHORT SETUP (SELL)</h3>
                    <div class="lbl">Entry Price:</div>
                    <div class="val">₹{entry_price:.2f}</div>
                    <hr style="border-color: #38435a;">
                    <div class="lbl">Target (+1.5R):</div>
                    <div class="val" style="color: #00c805;">₹{short_target:.2f}</div>
                    <hr style="border-color: #38435a;">
                    <div class="lbl">Stop Loss (-1.0R):</div>
                    <div class="val" style="color: #ff3b30;">₹{short_stop:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error processing ticker {symbol}. Make sure the symbol is correct and the market was open on that date. ({e})")
