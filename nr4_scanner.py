"""
NR4 Scanner and Daily EMA20 Trend Qualification.
Uses strictly completed historical daily trading sessions.
"""
import pandas as pd
from typing import Dict, Any

class NR4Scanner:
    @staticmethod
    def evaluate_nr4(daily_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validates whether the latest COMPLETED daily session is an NR4 day.
        NR4 Rule: Range(today-1) <= min(Range(today-2), Range(today-3), Range(today-4))
        """
        result = {
            "is_nr4": False,
            "daily_range": 0.0,
            "daily_range_pct": 0.0,
            "daily_ema20": 0.0,
            "daily_close": 0.0,
            "daily_state": "MISSING_DATA",
            "last_completed_date": None,
            "prev_ranges": []
        }
        
        if daily_df is None or len(daily_df) < 25:
            # Requires at least 20 periods for EMA20 + 4 days for NR4 window
            return result
        
        df = daily_df.copy()
        df['range'] = df['high'] - df['low']
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        
        # Take completed sessions: index -1 represents the most recently completed day
        completed_candles = df.iloc[-4:].copy()
        ranges = completed_candles['range'].tolist()
        
        target_range = ranges[-1]
        prior_three = ranges[:-1]
        
        result["daily_range"] = round(target_range, 2)
        result["prev_ranges"] = [round(r, 2) for r in prior_three]
        
        latest_candle = df.iloc[-1]
        result["daily_close"] = float(latest_candle['close'])
        result["daily_ema20"] = round(float(latest_candle['ema20']), 2)
        result["last_completed_date"] = str(latest_candle.name if hasattr(latest_candle, 'name') else latest_candle.get('timestamp', 'N/A'))
        
        if result["daily_close"] > 0:
            result["daily_range_pct"] = round((target_range / result["daily_close"]) * 100, 2)

        # Classification
        if result["daily_close"] > result["daily_ema20"]:
            result["daily_state"] = "ABOVE"
        elif result["daily_close"] < result["daily_ema20"]:
            result["daily_state"] = "BELOW"
        else:
            result["daily_state"] = "EQUAL"
            
        # NR4 Condition: Current completed range <= each of preceding 3 completed ranges
        if target_range <= min(prior_three):
            result["is_nr4"] = True
            
        return result

