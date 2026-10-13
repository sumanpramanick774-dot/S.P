from datetime import datetime
from pullback_engine import PullbackEngine

def test_pullback_qualification():
    engine = PullbackEngine(proximity_threshold_pct=0.25)
    now = datetime.now()
    
    # Test valid Bullish Pullback
    res = engine.evaluate(
        symbol="TCS",
        nr4_qualified=True,
        daily_state="ABOVE",
        intraday_state="ABOVE",
        c5_close=100.20,
        c5_high=100.50,
        c5_low=100.00,
        ema20_5m=100.00, # distance is +0.20% <= 0.25%
        ema50_5m=98.00,  # close > ema50
        rsi14=55.0,
        current_oi=50000,
        candle_timestamp=now
    )
    
    assert res["active"] is True
    assert res["status"] == "BULLISH PULLBACK"
    assert res["baseline_oi"] == 50000

