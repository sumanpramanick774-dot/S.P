"""
Central Data Orchestration & Multi-Timeframe Alignment Manager.
Prunes incomplete candles, coordinates scans, and computes composite signals.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

from config import IST, AppConfig
from indicators import calculate_ema, calculate_rsi, aggregate_candles
from nr4_scanner import NR4Scanner
from oi_engine import FuturesOIEngine
from pullback_engine import PullbackEngine

class DataManager:
    def __init__(self, dhan_client, instrument_manager):
        self.client = dhan_client
        self.instruments = instrument_manager
        self.oi_engine = FuturesOIEngine()
        self.pullback_engine = PullbackEngine(proximity_threshold_pct=AppConfig.PULLBACK_THRESHOLD_PCT)
        
        self.nr4_cache: Dict[str, Dict] = {}
        self.last_update_ts: str = "Never"
        self.invalid_symbols: List[str] = []
        self.missing_data_symbols: List[str] = []

    def run_daily_scan(self, universe: list[str]) -> Dict[str, Dict]:
        """
        Scans completed daily sessions for NR4 eligibility.
        Caches results so today's live price does not alter yesterday's classification.
        """
        results = {}
        self.invalid_symbols = []
        
        for sym in universe:
            sec_id = self.instruments.cash_map.get(sym)
            if not sec_id:
                self.invalid_symbols.append(sym)
                continue
                
            daily_df = self.client.get_historical_daily(sec_id)
            if daily_df.empty:
                self.missing_data_symbols.append(sym)
                continue
                
            scan_res = NR4Scanner.evaluate_nr4(daily_df)
            results[sym] = scan_res
            
        self.nr4_cache = results
        self.last_update_ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        return results

    def process_stock_intraday(self, symbol: str) -> Dict[str, Any]:
        """
        Calculates 5m, 15m, 30m, and 60m indicators from completed candles only.
        """
        sec_id = self.instruments.cash_map.get(symbol)
        fut_info = self.instruments.futures_map.get(symbol, {})
        fut_id = fut_info.get("security_id")
        
        summary = {
            "symbol": symbol,
            "nr4_qualified": False,
            "daily_state": "MISSING",
            "5m_state": "MISSING",
            "15m_state": "MISSING",
            "30m_state": "MISSING",
            "60m_state": "MISSING",
            "combined_state": "MISSING DATA",
            "5m_close": 0.0,
            "ema20_5m": 0.0,
            "ema50_5m": 0.0,
            "dist_ema20_pct": 0.0,
            "rsi_5m": 50.0,
            "rsi_15m": 50.0,
            "rsi_30m": 50.0,
            "rsi_60m": 50.0,
            "futures_oi": 0,
            "oi_change": 0,
            "oi_change_pct": 0.0,
            "oi_trend": "DATA UNAVAILABLE",
            "pullback_state": "NONE",
            "data_status": "OK",
            "candles_5m": pd.DataFrame()
        }

        # Check NR4 daily state
        daily_data = self.nr4_cache.get(symbol)
        if daily_data:
            summary["nr4_qualified"] = daily_data["is_nr4"]
            summary["daily_state"] = daily_data["daily_state"]

        if not sec_id:
            summary["data_status"] = "INVALID_SYMBOL"
            return summary

        # 1. Fetch 5m candles
        df_5m = self.client.get_intraday_candles(sec_id, interval="5")
        if df_5m.empty or len(df_5m) < 25:
            summary["data_status"] = "INSUFFICIENT_DATA"
            return summary

        # Prune current forming candle: ensure we only calculate on completed session blocks
        df_5m = df_5m.iloc[:-1].copy() if len(df_5m) > 1 else df_5m
        summary["candles_5m"] = df_5m

        # Compute 5m indicators
        df_5m['ema20'] = calculate_ema(df_5m['close'], 20)
        df_5m['ema50'] = calculate_ema(df_5m['close'], 50)
        df_5m['rsi14'] = calculate_rsi(df_5m['close'], 14)

        latest_5m = df_5m.iloc[-1]
        c5 = float(latest_5m['close'])
        e20_5 = float(latest_5m['ema20'])
        e50_5 = float(latest_5m['ema50'])
        r5 = float(latest_5m['rsi14'])

        summary["5m_close"] = round(c5, 2)
        summary["ema20_5m"] = round(e20_5, 2)
        summary["ema50_5m"] = round(e50_5, 2)
        summary["rsi_5m"] = round(r5, 1)
        summary["dist_ema20_pct"] = round(((c5 - e20_5) / e20_5) * 100, 2) if e20_5 > 0 else 0.0
        summary["5m_state"] = "ABOVE" if c5 > e20_5 else ("BELOW" if c5 < e20_5 else "EQUAL")

        # 2. Multi-timeframe aggregations
        df_15m = aggregate_candles(df_5m, '15min')
        df_30m = aggregate_candles(df_5m, '30min')
        df_60m = aggregate_candles(df_5m, '60min')

        states = [summary["5m_state"]]

        # 15m
        if len(df_15m) >= 20:
            df_15m['ema20'] = calculate_ema(df_15m['close'], 20)
            df_15m['rsi14'] = calculate_rsi(df_15m['close'], 14)
            c15 = df_15m.iloc[-1]['close']
            e15 = df_15m.iloc[-1]['ema20']
            summary["rsi_15m"] = round(float(df_15m.iloc[-1]['rsi14']), 1)
            summary["15m_state"] = "ABOVE" if c15 > e15 else ("BELOW" if c15 < e15 else "EQUAL")
            states.append(summary["15m_state"])
        else:
            summary["15m_state"] = "MISSING DATA"

        # 30m
        if len(df_30m) >= 20:
            df_30m['ema20'] = calculate_ema(df_30m['close'], 20)
            df_30m['rsi14'] = calculate_rsi(df_30m['close'], 14)
            c30 = df_30m.iloc[-1]['close']
            e30 = df_30m.iloc[-1]['ema20']
            summary["rsi_30m"] = round(float(df_30m.iloc[-1]['rsi14']), 1)
            summary["30m_state"] = "ABOVE" if c30 > e30 else ("BELOW" if c30 < e30 else "EQUAL")
            states.append(summary["30m_state"])
        else:
            summary["30m_state"] = "MISSING DATA"

        # 60m
        if len(df_60m) >= 20:
            df_60m['ema20'] = calculate_ema(df_60m['close'], 20)
            df_60m['rsi14'] = calculate_rsi(df_60m['close'], 14)
            c60 = df_60m.iloc[-1]['close']
            e60 = df_60m.iloc[-1]['ema20']
            summary["rsi_60m"] = round(float(df_60m.iloc[-1]['rsi14']), 1)
            summary["60m_state"] = "ABOVE" if c60 > e60 else ("BELOW" if c60 < e60 else "EQUAL")
            states.append(summary["60m_state"])
        else:
            summary["60m_state"] = "MISSING DATA"

        # Composite Classification
        if any(s == "MISSING DATA" for s in [summary["5m_state"], summary["15m_state"], summary["30m_state"], summary["60m_state"]]):
            summary["combined_state"] = "MISSING DATA"
        elif all(s == "ABOVE" for s in states) and len(states) == 4:
            summary["combined_state"] = "ABOVE"
        elif all(s == "BELOW" for s in states) and len(states) == 4:
            summary["combined_state"] = "BELOW"
        else:
            summary["combined_state"] = "NEUTRAL"

        # 3. Futures Open Interest
        if fut_id:
            oi_quote = self.client.get_futures_quote_oi(fut_id)
            current_oi = oi_quote.get("oi", 0)
            expiry = fut_info.get("expiry", "N/A")
            oi_metrics = self.oi_engine.update_oi(symbol, current_oi, datetime.now(IST), expiry)
            summary["futures_oi"] = oi_metrics["current_oi"]
            summary["oi_change"] = oi_metrics["oi_change"]
            summary["oi_change_pct"] = oi_metrics["oi_change_pct"]
            summary["oi_trend"] = oi_metrics["trend"]

        # 4. Pullback State Tracking
        candle_ts = latest_5m.name if isinstance(latest_5m.name, datetime) else datetime.now(IST)
        pullback_res = self.pullback_engine.evaluate(
            symbol=symbol,
            nr4_qualified=summary["nr4_qualified"],
            daily_state=summary["daily_state"],
            intraday_state=summary["combined_state"],
            c5_close=c5,
            c5_high=float(latest_5m['high']),
            c5_low=float(latest_5m['low']),
            ema20_5m=e20_5,
            ema50_5m=e50_5,
            rsi14=r5,
            current_oi=summary["futures_oi"],
            candle_timestamp=candle_ts
        )
        summary["pullback_state"] = pullback_res["status"]
        summary["pullback_details"] = pullback_res

        return summary

