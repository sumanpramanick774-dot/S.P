"""
Global Configuration, Timelines, Constants and Default Parameters.
"""
from dataclasses import dataclass
from zoneinfo import ZoneInfo
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Market timings in IST
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# Initial default Universe: Core NSE F&O High-Beta Liquid Stocks
DEFAULT_FNO_UNIVERSE = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "BHARTIARTL", "LT", "TATAMOTORS", "TATASTEEL",
    "AXISBANK", "KOTAKBANK", "MARUTI", "BAJFINANCE", "TITAN",
    "HINDUNILVR", "ITC", "SUNPHARMA", "JSWSTEEL", "ADANIENT"
]

@dataclass(frozen=True)
class AppConfig:
    PULLBACK_THRESHOLD_PCT: float = 0.25
    RSI_PERIOD: int = 14
    EMA_FAST: int = 20
    EMA_SLOW: int = 50
    INTRADAY_TIMEFRAMES = ["5m", "15m", "30m", "60m"]
    DHAN_SCRIP_MASTER_URL: str = "https://images.dhan.co/api-data/api-scrip-master.csv"

