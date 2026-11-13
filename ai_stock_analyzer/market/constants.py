from datetime import time


PRE_OPEN_START = time(9, 0)
PRE_OPEN_END = time(9, 15)
SESSION_OPEN = time(9, 15)
SESSION_CLOSE = time(15, 30)
SESSION_MINUTES = 375

INTERVAL_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "1d": None,
}

INTRADAY_INTERVALS = ("1m", "3m", "5m", "15m")

DAILY_INTERVAL = "1d"
