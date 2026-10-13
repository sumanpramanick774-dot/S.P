"""
Streamlit Live NR4 + EMA20 Multi-Timeframe Production Dashboard.
Read-Only Execution Engine.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from config import AppConfig, DEFAULT_FNO_UNIVERSE, IST
from dhan_client import DhanClientWrapper
from instrument_master import InstrumentManager
from data_manager import DataManager
from dashboard_components import build_candlestick_chart, build_rsi_chart, format_cell_state

st.set_page_config(
    page_title="NR4 + EMA20 Multi-Timeframe Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- SESSION STATE & INITIALIZATION -----------------
def get_credentials():
    """Reads secrets safely without throwing fatal error if missing."""
    client_id = None
    access_token = None
    if "DHAN_CLIENT_ID" in st.secrets:
        client_id = str(st.secrets["DHAN_CLIENT_ID"])
    if "DHAN_ACCESS_TOKEN" in st.secrets:
        access_token = str(st.secrets["DHAN_ACCESS_TOKEN"])
    return client_id, access_token

client_id, access_token = get_credentials()

if "instrument_mgr" not in st.session_state:
    st.session_state.instrument_mgr = InstrumentManager()
    st.session_state.instrument_mgr.fetch_and_build_universe(DEFAULT_FNO_UNIVERSE)

if "dhan_client" not in st.session_state:
    st.session_state.dhan_client = DhanClientWrapper(client_id, access_token)

if "data_manager" not in st.session_state:
    st.session_state.data_manager = DataManager(
        st.session_state.dhan_client, 
        st.session_state.instrument_mgr
    )
    # Pre-run daily scan
    st.session_state.data_manager.run_daily_scan(DEFAULT_FNO_UNIVERSE)

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.title("⚡ Control Panel")
    
    # Mode badge
    if st.session_state.dhan_client.is_connected:
        st.success("🟢 Connected to DhanHQ Live API")
    else:
        st.warning("🟠 Sandbox / Synthetic Demo Mode")
        st.caption("Valid credentials not detected in `.streamlit/secrets.toml`. Running strictly labeled synthetic simulations.")

    refresh_rate = st.slider("Auto-Refresh Rate (Seconds)", min_value=15, max_value=300, value=60)
    
    if st.button("🔄 Trigger Immediate Refresh", use_container_width=True):
        st.session_state.data_manager.run_daily_scan(DEFAULT_FNO_UNIVERSE)
        st.rerun()

    st.markdown("---")
    st.subheader("Filter Universe")
    selected_symbols = st.multiselect(
        "Active Stocks", 
        options=DEFAULT_FNO_UNIVERSE, 
        default=DEFAULT_FNO_UNIVERSE[:10]
    )
    
    st.caption(f"Last Instrument Sync: {st.session_state.instrument_mgr.last_sync.strftime('%H:%M:%S IST') if st.session_state.instrument_mgr.last_sync else 'N/A'}")

# ----------------- TOP STATUS BAR -----------------
now_ist = datetime.now(IST).strftime("%A, %d %B %Y | %I:%M:%S %p IST")
st.subheader("NR4 + EMA20 Multi-Timeframe Dashboard")
status_col1, status_col2, status_col3 = st.columns([2, 1, 1])
with status_col1:
    st.caption(f"Market Clock: **{now_ist}**")
with status_col2:
    st.caption(f"Data Health: **{'HEALTHY' if not st.session_state.data_manager.invalid_symbols else 'PARTIAL'}**")
with status_col3:
    st.caption(f"Last Scan: **{st.session_state.data_manager.last_update_ts}**")

# ----------------- BATCH PROCESSING -----------------
records = []
stock_details = {}

with st.spinner("Processing Multi-Timeframe Completeness & Futures OI..."):
    for sym in selected_symbols:
        summary = st.session_state.data_manager.process_stock_intraday(sym)
        stock_details[sym] = summary
        
        records.append({
            "Symbol": sym,
            "NR4": "✅ YES" if summary["nr4_qualified"] else "❌ NO",
            "Daily": summary["daily_state"],
            "5m": summary["5m_state"],
            "15m": summary["15m_state"],
            "30m": summary["30m_state"],
            "1H": summary["60m_state"],
            "Alignment": summary["combined_state"],
            "5m Close": summary["5m_close"],
            "EMA20 Dist %": f"{summary['dist_ema20_pct']}%",
            "5m RSI": summary["rsi_5m"],
            "Futures OI": f"{summary['futures_oi']:,}",
            "OI Chg %": f"{summary['oi_change_pct']}%",
            "OI Trend": summary["oi_trend"],
            "Pullback Alert": summary["pullback_state"],
            "Data Status": summary["data_status"]
        })

df_display = pd.DataFrame(records)

# ----------------- SUMMARY METRIC CARDS -----------------
m1, m2, m3, m4, m5 = st.columns(5)
total_nr4 = sum(1 for r in records if "YES" in r["NR4"])
bull_align = sum(1 for r in records if r["Alignment"] == "ABOVE")
bear_align = sum(1 for r in records if r["Alignment"] == "BELOW")
active_pullbacks = sum(1 for r in records if "PULLBACK" in r["Pullback Alert"])
missing_data_count = sum(1 for r in records if r["Data Status"] != "OK")

m1.metric("NR4 Qualified", total_nr4)
m2.metric("Intraday ABOVE", bull_align)
m3.metric("Intraday BELOW", bear_align)
m4.metric("Pullback Candidates", active_pullbacks)
m5.metric("Missing / Stale", missing_data_count)

# ----------------- DASHBOARD TABS -----------------
tab_overview, tab_nr4, tab_mtf, tab_oi, tab_pullback, tab_details, tab_health = st.tabs([
    "Market Overview",
    "NR4 Watchlist",
    "Multi-Timeframe Scanner",
    "Futures OI Monitor",
    "EMA20 Pullback Monitor",
    "Stock Deep Dive",
    "Data Health & Logs"
])

with tab_overview:
    st.subheader("Institutional Multi-Timeframe Alignment Matrix")
    st.dataframe(
        df_display.style.map(format_cell_state, subset=["Daily", "5m", "15m", "30m", "1H", "Alignment"]),
        use_container_width=True,
        height=400
    )

with tab_nr4:
    st.subheader("Daily NR4 Range Contraction Universe")
    st.caption("Determined strictly from previous completed daily trading sessions.")
    nr4_df = df_display[df_display["NR4"] == "✅ YES"]
    if not nr4_df.empty:
        st.dataframe(nr4_df, use_container_width=True)
    else:
        st.info("No stocks qualified as NR4 in the selected universe for the latest completed daily session.")

with tab_mtf:
    st.subheader("Intraday Quad-Timeframe EMA20 Alignment (5m, 15m, 30m, 60m)")
    st.dataframe(
        df_display[["Symbol", "Daily", "5m", "15m", "30m", "1H", "Alignment", "EMA20 Dist %", "5m RSI"]].style.map(
            format_cell_state, subset=["Daily", "5m", "15m", "30m", "1H", "Alignment"]
        ),
        use_container_width=True
    )

with tab_oi:
    st.subheader("NSE Stock Futures Open Interest Engine")
    st.caption("Active near-month futures contract tracking relative to session baseline.")
    st.dataframe(
        df_display[["Symbol", "Futures OI", "OI Chg %", "OI Trend", "5m Close", "Alignment"]],
        use_container_width=True
    )

with tab_pullback:
    st.subheader("Deterministic EMA20 Pullback Alerts")
    st.caption("Qualified when aligned stock approaches 5m EMA20 within 0.25% while respecting EMA50.")
    pb_col1, pb_col2 = st.columns(2)
    
    bullish_pb = [r for r in records if "BULLISH PULLBACK" in r["Pullback Alert"]]
    bearish_pb = [r for r in records if "BEARISH PULLBACK" in r["Pullback Alert"]]
    
    with pb_col1:
        st.success(f"🟢 Bullish Pullback Candidates ({len(bullish_pb)})")
        if bullish_pb:
            st.dataframe(pd.DataFrame(bullish_pb)[["Symbol", "5m Close", "EMA20 Dist %", "Futures OI", "OI Chg %"]], use_container_width=True)
        else:
            st.write("No active bullish pullbacks.")
            
    with pb_col2:
        st.error(f"🔴 Bearish Pullback Candidates ({len(bearish_pb)})")
        if bearish_pb:
            st.dataframe(pd.DataFrame(bearish_pb)[["Symbol", "5m Close", "EMA20 Dist %", "Futures OI", "OI Chg %"]], use_container_width=True)
        else:
            st.write("No active bearish pullbacks.")

with tab_details:
    st.subheader("Single-Stock Technical Inspector")
    target_sym = st.selectbox("Select Symbol to Inspect", options=selected_symbols)
    
    if target_sym in stock_details:
        target_info = stock_details[target_sym]
        c_df = target_info.get("candles_5m", pd.DataFrame())
        
        if not c_df.empty:
            st.plotly_chart(build_candlestick_chart(c_df, target_sym), use_container_width=True)
            st.plotly_chart(build_rsi_chart(c_df), use_container_width=True)
        else:
            st.warning("Insufficient intraday candles to render candlestick visualization.")
            
        st.markdown("#### Contract & Pullback Diagnostic Readout")
        diag_col1, diag_col2, diag_col3 = st.columns(3)
        diag_col1.metric("5m EMA20", target_info["ema20_5m"])
        diag_col2.metric("5m EMA50", target_info["ema50_5m"])
        diag_col3.metric("Pullback Baseline OI", target_info["pullback_details"].get("baseline_oi", "None"))

with tab_health:
    st.subheader("Data Freshness, API Endpoints, and Diagnostic Audit")
    st.json({
        "API_Connected": st.session_state.dhan_client.is_connected,
        "Last_API_Error": st.session_state.dhan_client.last_error or "None",
        "Instrument_Master_URL": AppConfig.DHAN_SCRIP_MASTER_URL,
        "Total_Cash_Mapped": len(st.session_state.instrument_mgr.cash_map),
        "Total_Futures_Mapped": len(st.session_state.instrument_mgr.futures_map),
        "Invalid_Symbols": st.session_state.data_manager.invalid_symbols,
        "Missing_Data_Symbols": st.session_state.data_manager.missing_data_symbols
    })

