from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Mapping, Sequence

from .clock import IST
from .constants import DAILY_INTERVAL, INTERVAL_MINUTES, SESSION_CLOSE, SESSION_OPEN
from .symbols import canonical_symbol


class BarError(ValueError):
    pass


@dataclass(frozen=True)
class Bar:
    symbol: str
    interval: str
    start: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: float | None = None

    def __post_init__(self) -> None:
        if self.interval not in INTERVAL_MINUTES:
            raise BarError(f"Unsupported interval: {self.interval}")
        if not isinstance(self.start, datetime):
            raise BarError("Bar start must be a datetime")
        if self.start.tzinfo is None:
            raise BarError("Bar start must be timezone-aware")

        start = self.start.astimezone(IST)
        if self.interval == DAILY_INTERVAL:
            if start.time() != time.min:
                raise BarError("Daily bar start must be midnight IST")
        else:
            minutes = INTERVAL_MINUTES[self.interval]
            if minutes is None:
                raise BarError(f"Unsupported interval: {self.interval}")
            session_open = datetime.combine(start.date(), SESSION_OPEN, tzinfo=IST)
            session_close = datetime.combine(start.date(), SESSION_CLOSE, tzinfo=IST)
            if start < session_open:
                raise BarError("Bar start is before the NSE session open")
            if start + timedelta(minutes=minutes) > session_close:
                raise BarError("Bar extends beyond the NSE session close")
            if start.second or start.microsecond:
                raise BarError("Bar start must be aligned to the minute")
            if (start.hour * 60 + start.minute) % minutes != 0:
                raise BarError(f"Bar start is not aligned to the {self.interval} grid")

        prices = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
        }
        for name, value in prices.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise BarError(f"Bar {name} must be numeric")
            if not math.isfinite(float(value)):
                raise BarError(f"Bar {name} must be finite")
            if float(value) <= 0:
                raise BarError(f"Bar {name} must be positive")
        if isinstance(self.volume, bool) or not isinstance(self.volume, (int, float)):
            raise BarError("Bar volume must be numeric")
        if not math.isfinite(float(self.volume)) or float(self.volume) < 0:
            raise BarError("Bar volume must be finite and non-negative")
        if self.open_interest is not None:
            if isinstance(self.open_interest, bool) or not isinstance(
                self.open_interest, (int, float)
            ):
                raise BarError("Bar open_interest must be numeric")
            if (
                not math.isfinite(float(self.open_interest))
                or float(self.open_interest) < 0
            ):
                raise BarError("Bar open_interest must be finite and non-negative")

        if self.high < max(self.open, self.close):
            raise BarError("Bar high is below open or close")
        if self.low > min(self.open, self.close):
            raise BarError("Bar low is above open or close")
        if self.high < self.low:
            raise BarError("Bar high is below low")

        object.__setattr__(self, "symbol", canonical_symbol(self.symbol))
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "open", float(self.open))
        object.__setattr__(self, "high", float(self.high))
        object.__setattr__(self, "low", float(self.low))
        object.__setattr__(self, "close", float(self.close))
        object.__setattr__(self, "volume", float(self.volume))
        if self.open_interest is not None:
            object.__setattr__(self, "open_interest", float(self.open_interest))

    @property
    def session_date(self) -> date:
        return self.start.date()

    @property
    def is_daily(self) -> bool:
        return self.interval == DAILY_INTERVAL

    @property
    def end(self) -> datetime:
        if self.is_daily:
            return datetime.combine(self.start.date(), SESSION_CLOSE, tzinfo=IST)
        minutes = INTERVAL_MINUTES[self.interval]
        if minutes is None:
            raise BarError(f"Unsupported interval: {self.interval}")
        return self.start + timedelta(minutes=minutes)

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "start": self.start.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "open_interest": self.open_interest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Bar":
        raw_start = str(payload["start"]).replace("Z", "+00:00")
        oi = payload.get("open_interest")
        return cls(
            symbol=str(payload["symbol"]),
            interval=str(payload["interval"]),
            start=datetime.fromisoformat(raw_start),
            open=float(payload["open"]),
            high=float(payload["high"]),
            low=float(payload["low"]),
            close=float(payload["close"]),
            volume=float(payload["volume"]),
            open_interest=float(oi) if oi is not None else None,
        )


def sort_bars(bars: Iterable[Bar]) -> list[Bar]:
    return sorted(bars, key=lambda bar: bar.start)


def duplicate_starts(bars: Iterable[Bar]) -> list[datetime]:
    seen: set[datetime] = set()
    duplicates: list[datetime] = []
    for bar in bars:
        if bar.start in seen and bar.start not in duplicates:
            duplicates.append(bar.start)
        seen.add(bar.start)
    return duplicates


def dedupe_bars(bars: Iterable[Bar], keep: str = "last") -> list[Bar]:
    if keep not in {"first", "last"}:
        raise ValueError("keep must be 'first' or 'last'")
    ordered = sort_bars(bars)
    result: dict[datetime, Bar] = {}
    for bar in ordered:
        if keep == "first" and bar.start in result:
            continue
        result[bar.start] = bar
    return [result[key] for key in sorted(result)]


def group_by_day(bars: Iterable[Bar]) -> dict[date, list[Bar]]:
    grouped: dict[date, list[Bar]] = {}
    for bar in bars:
        grouped.setdefault(bar.session_date, []).append(bar)
    return {day: sort_bars(items) for day, items in grouped.items()}


def validate_bar_series(
    bars: Sequence[Bar],
    symbol: str | None = None,
    interval: str | None = None,
) -> list[str]:
    issues: list[str] = []
    if not bars:
        return ["No bars"]
    expected_symbol = canonical_symbol(symbol) if symbol else bars[0].symbol
    expected_interval = interval or bars[0].interval
    for bar in bars:
        if bar.symbol != expected_symbol:
            issues.append(f"Mixed symbols: {bar.symbol}")
            break
    for bar in bars:
        if bar.interval != expected_interval:
            issues.append(f"Mixed intervals: {bar.interval}")
            break
    duplicates = duplicate_starts(bars)
    if duplicates:
        issues.append(f"Duplicate bar starts: {len(duplicates)}")
    if any(bars[index].start > bars[index + 1].start for index in range(len(bars) - 1)):
        issues.append("Bars are not sorted by start time")
    return issues


def missing_starts(
    bars: Iterable[Bar], expected_starts: Iterable[datetime]
) -> list[datetime]:
    present = {bar.start for bar in bars}
    return [start for start in expected_starts if start not in present]
