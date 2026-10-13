import pandas as pd
import numpy as np
from indicators import calculate_ema, calculate_rsi, aggregate_candles

def test_ema_calculation():
    s = pd.Series([10.0] * 30)
    ema = calculate_ema(s, 20)
    assert round(ema.iloc[-1], 2) == 10.0

def test_rsi_range():
    # Monotonically increasing prices -> RSI should be high
    s = pd.Series([float(i) for i in range(1, 50)])
    rsi = calculate_rsi(s, 14)
    assert 90.0 <= rsi.iloc[-1] <= 100.0

def test_candle_aggregation():
    # Create 3 5-minute candles to make 1 15-minute candle
    times = pd.date_range("2026-10-13 09:15:00", periods=3, freq="5min")
    df_5m = pd.DataFrame({
        "open": [100, 102, 101],
        "high": [103, 105, 104],
        "low": [99, 101, 100],
        "close": [102, 101, 106],
        "volume": [100, 200, 300]
    }, index=times)
    
    agg = aggregate_candles(df_5m, "15min")
    assert len(agg) == 1
    assert agg.iloc[0]["open"] == 100
    assert agg.iloc[0]["high"] == 105
    assert agg.iloc[0]["low"] == 99
    assert agg.iloc[0]["close"] == 106
    assert agg.iloc[0]["volume"] == 600

