import streamlit as st
import pandas as pd
from datetime import datetime
from config import AppConfig, DEFAULT_FNO_UNIVERSE, IST
from dhan_client import DhanClientWrapper
from instrument_master import InstrumentManager
from data_manager import DataManager
from dashboard_components import build_candlestick_chart, build_rsi_chart, format_cell_state

st.set_page_config(page_title="NR4 + EMA20 Live Dashboard", page_icon="⚡", layout="wide")

# ইনস্ট্রুমেন্ট লিস্ট একবারই লোড হবে
if "instrument_mgr" not in st.session_state:
    st.session_state.instrument_mgr = InstrumentManager()
    st.session_state.instrument_mgr.fetch_and_build_universe(DEFAULT_FNO_UNIVERSE)

# সাইডবারে আইডি এবং টোকেন দেওয়ার ব্যবস্থা
with st.sidebar:
    st.title("🔐 API Credentials")
    st.write("আপনার আইডি এবং টোকেন এখানে দিন। অ্যাপ বন্ধ করলে এটি মুছে যাবে।")
    
    input_id = st.text_input("Dhan Client ID", type="password")
    input_token = st.text_input("Dhan Access Token", type="password")
    
    if st.button("Connect API", use_container_width=True):
        if input_id and input_token:
            # নতুন ক্রেডেনশিয়াল দিয়ে কানেক্ট করা হচ্ছে
            st.session_state.dhan_client = DhanClientWrapper(input_id, input_token)
            st.session_state.data_manager = DataManager(st.session_state.dhan_client, st.session_state.instrument_mgr)
            st.session_state.data_manager.run_daily_scan(DEFAULT_FNO_UNIVERSE)
            st.success("Connected Successfully!")
            st.rerun()
        else:
            st.error("দয়া করে আইডি এবং টোকেন দুটোই দিন।")

    st.markdown("---")
    st.title("⚡ Settings")
    
    is_connected = "dhan_client" in st.session_state and st.session_state.dhan_client.is_connected
    
    if is_connected:
        st.success("🟢 DhanHQ Connected (Live Data)")
    else:
        st.warning("🟠 Sandbox / Synthetic Mode")
        
    if st.button("🔄 Refresh Data", use_container_width=True):
        if "data_manager" in st.session_state:
            st.session_state.data_manager.run_daily_scan(DEFAULT_FNO_UNIVERSE)
        st.rerun()
        
    selected_symbols = st.multiselect("Active Symbols", DEFAULT_FNO_UNIVERSE, DEFAULT_FNO_UNIVERSE[:10])

# যদি কানেক্ট না করা থাকে, তবে ডেমো মোডে চলবে
if "dhan_client" not in st.session_state:
    st.session_state.dhan_client = DhanClientWrapper(None, None)
if "data_manager" not in st.session_state:
    st.session_state.data_manager = DataManager(st.session_state.dhan_client, st.session_state.instrument_mgr)
    st.session_state.data_manager.run_daily_scan(DEFAULT_FNO_UNIVERSE)

# মেইন ড্যাশবোর্ড
now_ist = datetime.now(IST).strftime("%A, %d %B %Y | %I:%M:%S %p IST")
st.subheader("NR4 + EMA20 Multi-Timeframe Dashboard")
st.caption(f"Clock: {now_ist} | Last Scan: {st.session_state.data_manager.last_update_ts}")

records = []
stock_details = {}
for sym in selected_symbols:
    s = st.session_state.data_manager.process_stock_intraday(sym)
    stock_details[sym] = s
    records.append({"Symbol": sym, "NR4": "✅ YES" if s["nr4_qualified"] else "❌ NO", "Daily": s["daily_state"], "5m": s["5m_state"], "15m": s["15m_state"], "30m": s["30m_state"], "1H": s["60m_state"], "Alignment": s["combined_state"], "5m Close": s["5m_close"], "EMA20 Dist %": f"{s['dist_ema20_pct']}%", "5m RSI": s["rsi_5m"], "Futures OI": f"{s['futures_oi']:,}", "OI Chg %": f"{s['oi_change_pct']}%", "OI Trend": s["oi_trend"], "Pullback Alert": s["pullback_state"]})

df_display = pd.DataFrame(records)

c1, c2, c3, c4 = st.columns(4)
c1.metric("NR4 Stocks", sum(1 for r in records if "YES" in r["NR4"]))
c2.metric("Intraday ABOVE", sum(1 for r in records if r["Alignment"] == "ABOVE"))
c3.metric("Intraday BELOW", sum(1 for r in records if r["Alignment"] == "BELOW"))
c4.metric("Pullback Candidates", sum(1 for r in records if "PULLBACK" in r["Pullback Alert"]))

t1, t2, t3 = st.tabs(["Scanner Matrix", "Pullback Watchlist", "Stock Inspector"])
with t1:
    st.dataframe(df_display.style.map(format_cell_state, subset=["Daily", "5m", "15m", "30m", "1H", "Alignment"]), use_container_width=True)
with t2:
    pb_stocks = [r for r in records if "PULLBACK" in r["Pullback Alert"]]
    if pb_stocks:
        st.dataframe(pd.DataFrame(pb_stocks), use_container_width=True)
    else:
        st.info("No active pullbacks detected in the current candle.")
with t3:
    sym_choice = st.selectbox("Select Symbol", selected_symbols)
    if sym_choice in stock_details:
        c_df = stock_details[sym_choice].get("candles_5m", pd.DataFrame())
        if not c_df.empty:
            st.plotly_chart(build_candlestick_chart(c_df, sym_choice), use_container_width=True)
            st.plotly_chart(build_rsi_chart(c_df), use_container_width=True)
