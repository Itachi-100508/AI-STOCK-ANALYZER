from datetime import timedelta, timezone
from zoneinfo import ZoneInfo


try:
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")
