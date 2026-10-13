from datetime import datetime
from oi_engine import FuturesOIEngine

def test_oi_tracking_and_baseline():
    engine = FuturesOIEngine()
    ts = datetime.now()
    
    # 1. First tick sets baseline
    res1 = engine.update_oi("RELIANCE", 100000, ts, "2026-10-29")
    assert res1["baseline_oi"] == 100000
    assert res1["oi_change"] == 0
    assert res1["trend"] == "UNCHANGED"
    
    # 2. Increase in OI
    res2 = engine.update_oi("RELIANCE", 110000, ts, "2026-10-29")
    assert res2["oi_change"] == 10000
    assert res2["oi_change_pct"] == 10.0
    assert res2["trend"] == "INCREASING"

def test_oi_interpretation():
    assert FuturesOIEngine.get_oi_interpretation(True, True) == "Long Buildup"
    assert FuturesOIEngine.get_oi_interpretation(False, True) == "Short Buildup"
    assert FuturesOIEngine.get_oi_interpretation(True, False) == "Short Covering"
    assert FuturesOIEngine.get_oi_interpretation(False, False) == "Long Unwinding"

