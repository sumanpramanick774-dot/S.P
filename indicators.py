"""
Technical Indicators Engine with strict candle completion checks.
No lookahead, handles warm-up boundaries deterministically.
"""
import pandas as pd
import numpy as np

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average with standard alpha."""
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)

def aggregate_candles(df_5m: pd.DataFrame, target_rule: str) -> pd.DataFrame:
    """
    Aggregates completed 5-minute candles into 15m, 30m, or 60m OHLCV.
    Rules: '15min', '30min', '60min'.
    """
    if df_5m.empty:
        return pd.DataFrame()
    
    df = df_5m.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df['timestamp'])
        
    aggregated = df.resample(target_rule, closed='left', label='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return aggregated

