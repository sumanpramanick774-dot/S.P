"""
Deterministic EMA20 Pullback Engine.
Monitors price approaching 5m EMA20 with multi-timeframe alignment.
Maintains continuous state tracking across Streamlit session runs.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict

@dataclass
class PullbackState:
    symbol: str
    direction: str                     # "BULLISH" or "BEARISH"
    start_time: datetime
    start_price: float
    start_oi: int
    session_extreme_price: float       # High for bullish, Low for bearish
    last_update_time: datetime
    is_active: bool = True

class PullbackEngine:
    def __init__(self, proximity_threshold_pct: float = 0.25):
        self.proximity_threshold_pct = proximity_threshold_pct
        self.active_pullbacks: Dict[str, PullbackState] = {}

    def evaluate(self, 
                 symbol: str,
                 nr4_qualified: bool,
                 daily_state: str,
                 intraday_state: str,
                 c5_close: float,
                 c5_high: float,
                 c5_low: float,
                 ema20_5m: float,
                 ema50_5m: float,
                 rsi14: float,
                 current_oi: int,
                 candle_timestamp: datetime) -> Dict:
        """
        Evaluates deterministic pullback logic.
        """
        output = {
            "status": "NONE",
            "direction": None,
            "distance_pct": 0.0,
            "duration_mins": 0,
            "baseline_oi": None,
            "oi_delta": 0,
            "oi_delta_pct": 0.0,
            "active": False
        }

        if ema20_5m <= 0:
            return output

        distance_pct = ((c5_close - ema20_5m) / ema20_5m) * 100
        output["distance_pct"] = round(distance_pct, 2)

        # 1. Bullish Qualification Check
        is_bullish_candidate = (
            nr4_qualified and
            daily_state == "ABOVE" and
            intraday_state == "ABOVE" and
            c5_close >= ema50_5m and
            0.0 <= distance_pct <= self.proximity_threshold_pct
        )

        # 2. Bearish Qualification Check
        is_bearish_candidate = (
            nr4_qualified and
            daily_state == "BELOW" and
            intraday_state == "BELOW" and
            c5_close <= ema50_5m and
            -self.proximity_threshold_pct <= distance_pct <= 0.0
        )

        state = self.active_pullbacks.get(symbol)

        # Handle Bullish Pullback
        if is_bullish_candidate:
            if not state or not state.is_active or state.direction != "BULLISH":
                # Start new pullback session
                state = PullbackState(
                    symbol=symbol,
                    direction="BULLISH",
                    start_time=candle_timestamp,
                    start_price=c5_close,
                    start_oi=current_oi,
                    session_extreme_price=c5_high,
                    last_update_time=candle_timestamp,
                    is_active=True
                )
                self.active_pullbacks[symbol] = state
            else:
                # Update ongoing pullback
                state.session_extreme_price = max(state.session_extreme_price, c5_high)
                state.last_update_time = candle_timestamp

        # Handle Bearish Pullback
        elif is_bearish_candidate:
            if not state or not state.is_active or state.direction != "BEARISH":
                state = PullbackState(
                    symbol=symbol,
                    direction="BEARISH",
                    start_time=candle_timestamp,
                    start_price=c5_close,
                    start_oi=current_oi,
                    session_extreme_price=c5_low,
                    last_update_time=candle_timestamp,
                    is_active=True
                )
                self.active_pullbacks[symbol] = state
            else:
                state.session_extreme_price = min(state.session_extreme_price, c5_low)
                state.last_update_time = candle_timestamp

        # Termination / Exit Criteria
        elif state and state.is_active:
            # Exit if violated EMA50 or drifted outside proximity corridor
            if state.direction == "BULLISH" and (c5_close < ema50_5m or distance_pct > self.proximity_threshold_pct * 1.5):
                state.is_active = False
            elif state.direction == "BEARISH" and (c5_close > ema50_5m or distance_pct < -self.proximity_threshold_pct * 1.5):
                state.is_active = False

        # Format output
        if state and state.is_active:
            duration = int((candle_timestamp - state.start_time).total_seconds() / 60)
            oi_delta = current_oi - state.start_oi if state.start_oi > 0 else 0
            oi_delta_pct = (oi_delta / state.start_oi * 100) if state.start_oi > 0 else 0.0

            output.update({
                "status": f"{state.direction} PULLBACK",
                "direction": state.direction,
                "duration_mins": duration,
                "baseline_oi": state.start_oi,
                "oi_delta": oi_delta,
                "oi_delta_pct": round(oi_delta_pct, 2),
                "start_price": state.start_price,
                "extreme_price": state.session_extreme_price,
                "active": True
            })

        return output

