"""
Futures Open Interest Tracking Engine.
Tracks real contract OI, intraday OI variations, and session baseline trends.
"""
from datetime import datetime
from typing import Dict, Any, Optional

class FuturesOIEngine:
    def __init__(self):
        # symbol -> {baseline_oi, last_oi, timestamp, source}
        self.oi_store: Dict[str, Dict[str, Any]] = {}

    def update_oi(self, symbol: str, current_oi: int, timestamp: datetime, contract_expiry: str) -> Dict[str, Any]:
        """
        Updates OI and calculates metrics against session baseline.
        """
        if current_oi <= 0:
            return {
                "current_oi": 0,
                "oi_change": 0,
                "oi_change_pct": 0.0,
                "trend": "DATA UNAVAILABLE",
                "contract_expiry": contract_expiry,
                "baseline_oi": None,
                "timestamp": timestamp.strftime("%H:%M:%S")
            }

        if symbol not in self.oi_store or self.oi_store[symbol]["baseline_oi"] is None:
            self.oi_store[symbol] = {
                "baseline_oi": current_oi,
                "previous_5m_oi": current_oi,
                "last_oi": current_oi,
                "timestamp": timestamp,
                "contract_expiry": contract_expiry
            }

        entry = self.oi_store[symbol]
        baseline = entry["baseline_oi"]
        prev_5m = entry.get("previous_5m_oi", current_oi)
        
        oi_change = current_oi - baseline
        oi_change_pct = round((oi_change / baseline) * 100, 2) if baseline > 0 else 0.0

        if current_oi > entry["last_oi"]:
            trend = "INCREASING"
        elif current_oi < entry["last_oi"]:
            trend = "DECREASING"
        else:
            trend = "UNCHANGED"

        # Update last state
        entry["last_oi"] = current_oi
        entry["timestamp"] = timestamp

        return {
            "current_oi": current_oi,
            "previous_5m_oi": prev_5m,
            "oi_change": oi_change,
            "oi_change_pct": oi_change_pct,
            "trend": trend,
            "contract_expiry": contract_expiry,
            "baseline_oi": baseline,
            "timestamp": timestamp.strftime("%H:%M:%S")
        }

    def register_5m_oi(self, symbol: str, oi_5m: int):
        """Records 5m closed candle OI."""
        if symbol in self.oi_store and oi_5m > 0:
            self.oi_store[symbol]["previous_5m_oi"] = oi_5m

    @staticmethod
    def get_oi_interpretation(price_change_positive: bool, oi_change_positive: bool) -> str:
        """Determines derivative market interpretation."""
        if price_change_positive and oi_change_positive:
            return "Long Buildup"
        elif not price_change_positive and oi_change_positive:
            return "Short Buildup"
        elif price_change_positive and not oi_change_positive:
            return "Short Covering"
        else:
            return "Long Unwinding"

