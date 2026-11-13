from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from importlib import resources
from typing import Iterable, Mapping

from .clock import IST
from .constants import (
    DAILY_INTERVAL,
    INTERVAL_MINUTES,
    SESSION_CLOSE,
    SESSION_MINUTES,
    SESSION_OPEN,
)


class CalendarError(Exception):
    pass


class CalendarCoverageError(CalendarError):
    pass


class NotATradingDayError(CalendarError):
    pass


@dataclass(frozen=True)
class SpecialSession:
    day: date
    name: str
    regular_session: bool = False


@dataclass(frozen=True)
class HolidayData:
    year: int
    trading_holidays: Mapping[date, str]
    weekend_holidays: Mapping[date, str]
    special_sessions: Mapping[date, SpecialSession]
    source: str
    retrieved_at: date


@dataclass(frozen=True)
class TradingSession:
    day: date
    open: datetime
    close: datetime

    @property
    def is_regular(self) -> bool:
        return True


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def load_nse_holiday_data(year: int) -> HolidayData:
    resource = resources.files("ai_stock_analyzer.data").joinpath(
        f"nse_holidays_{year}.json"
    )
    if not resource.is_file():
        raise CalendarCoverageError(
            f"No verified NSE holiday data available for {year}"
        )
    payload = json.loads(resource.read_text(encoding="utf-8"))
    trading = {
        _parse_date(item["date"]): item["name"]
        for item in payload.get("trading_holidays", [])
    }
    weekend = {
        _parse_date(item["date"]): item["name"]
        for item in payload.get("weekend_holidays", [])
    }
    special = {
        _parse_date(item["date"]): SpecialSession(
            day=_parse_date(item["date"]),
            name=item["name"],
            regular_session=bool(item.get("regular_session", False)),
        )
        for item in payload.get("special_sessions", [])
    }
    return HolidayData(
        year=int(payload["year"]),
        trading_holidays=trading,
        weekend_holidays=weekend,
        special_sessions=special,
        source=str(payload.get("source", "")),
        retrieved_at=_parse_date(payload["retrieved_at"]),
    )


class NSECalendar:
    def __init__(
        self,
        holiday_data: Iterable[HolidayData] | None = None,
        allow_unverified_years: bool = False,
    ) -> None:
        if holiday_data is None:
            holiday_data = (load_nse_holiday_data(2026),)
        self._data = tuple(holiday_data)
        self._years = {item.year for item in self._data}
        self._allow_unverified_years = allow_unverified_years
        self._holidays: dict[date, str] = {}
        self._special: dict[date, SpecialSession] = {}
        for item in self._data:
            self._holidays.update(item.trading_holidays)
            self._holidays.update(item.weekend_holidays)
            self._special.update(item.special_sessions)

    @property
    def covered_years(self) -> frozenset[int]:
        return frozenset(self._years)

    def require_coverage(self, day: date) -> None:
        if day.year in self._years:
            return
        if self._allow_unverified_years:
            return
        raise CalendarCoverageError(
            f"No verified NSE holiday data for {day.year}; "
            f"covered years: {sorted(self._years)}"
        )

    def holiday_name(self, day: date) -> str | None:
        self.require_coverage(day)
        return self._holidays.get(day)

    def special_session(self, day: date) -> SpecialSession | None:
        self.require_coverage(day)
        return self._special.get(day)

    def is_weekend(self, day: date) -> bool:
        return day.weekday() >= 5

    def is_trading_day(self, day: date) -> bool:
        self.require_coverage(day)
        if self.is_weekend(day):
            return False
        if day in self._holidays:
            return False
        if day in self._special:
            return False
        return True

    def session(self, day: date) -> TradingSession | None:
        if not self.is_trading_day(day):
            return None
        return TradingSession(
            day=day,
            open=datetime.combine(day, SESSION_OPEN, tzinfo=IST),
            close=datetime.combine(day, SESSION_CLOSE, tzinfo=IST),
        )

    def session_open(self, day: date) -> datetime:
        session = self.session(day)
        if session is None:
            raise NotATradingDayError(f"{day.isoformat()} is not a regular trading day")
        return session.open

    def session_close(self, day: date) -> datetime:
        session = self.session(day)
        if session is None:
            raise NotATradingDayError(f"{day.isoformat()} is not a regular trading day")
        return session.close

    def next_trading_day(self, day: date, include_current: bool = False) -> date:
        cursor = day if include_current else day + timedelta(days=1)
        for _ in range(370):
            if self.is_trading_day(cursor):
                return cursor
            cursor += timedelta(days=1)
        raise CalendarCoverageError("No trading day found within the next year")

    def previous_trading_day(
        self, day: date, include_current: bool = False
    ) -> date:
        cursor = day if include_current else day - timedelta(days=1)
        for _ in range(370):
            if self.is_trading_day(cursor):
                return cursor
            cursor -= timedelta(days=1)
        raise CalendarCoverageError("No trading day found within the prior year")

    def trading_days(self, start: date, end: date) -> list[date]:
        if end < start:
            raise ValueError("end must be on or after start")
        result = []
        cursor = start
        while cursor <= end:
            if self.is_trading_day(cursor):
                result.append(cursor)
            cursor += timedelta(days=1)
        return result

    def expected_bar_count(self, interval: str) -> int:
        if interval == DAILY_INTERVAL:
            return 1
        if interval not in INTERVAL_MINUTES:
            raise ValueError(f"Unsupported interval: {interval}")
        minutes = INTERVAL_MINUTES[interval]
        if minutes is None or SESSION_MINUTES % minutes != 0:
            raise ValueError(f"Interval does not divide the NSE session: {interval}")
        return SESSION_MINUTES // minutes

    def session_bar_starts(self, day: date, interval: str) -> list[datetime]:
        if not self.is_trading_day(day):
            raise NotATradingDayError(f"{day.isoformat()} is not a regular trading day")
        if interval == DAILY_INTERVAL:
            return [datetime.combine(day, time.min, tzinfo=IST)]
        if interval not in INTERVAL_MINUTES:
            raise ValueError(f"Unsupported interval: {interval}")
        minutes = INTERVAL_MINUTES[interval]
        if minutes is None:
            raise ValueError(f"Unsupported interval: {interval}")
        if SESSION_MINUTES % minutes != 0:
            raise ValueError(f"Interval does not divide the NSE session: {interval}")

        starts: list[datetime] = []
        cursor = datetime.combine(day, SESSION_OPEN, tzinfo=IST)
        close = datetime.combine(day, SESSION_CLOSE, tzinfo=IST)
        step = timedelta(minutes=minutes)
        while cursor + step <= close:
            starts.append(cursor)
            cursor += step
        return starts

    def is_session_bar_start(
        self, day: date, start: datetime, interval: str
    ) -> bool:
        if start.tzinfo is None:
            return False
        local = start.astimezone(IST)
        if local.date() != day:
            return False
        if not self.is_trading_day(day):
            return False
        if interval == DAILY_INTERVAL:
            return local.time() == time.min
        if interval not in INTERVAL_MINUTES:
            return False
        minutes = INTERVAL_MINUTES[interval]
        if minutes is None:
            return False
        open_dt = datetime.combine(day, SESSION_OPEN, tzinfo=IST)
        close_dt = datetime.combine(day, SESSION_CLOSE, tzinfo=IST)
        if local < open_dt or local + timedelta(minutes=minutes) > close_dt:
            return False
        if local.second or local.microsecond:
            return False
        minute_of_day = local.hour * 60 + local.minute
        return minute_of_day % minutes == 0

    def bar_close(self, start: datetime, interval: str) -> datetime:
        if interval == DAILY_INTERVAL:
            return datetime.combine(start.date(), SESSION_CLOSE, tzinfo=IST)
        if interval not in INTERVAL_MINUTES:
            raise ValueError(f"Unsupported interval: {interval}")
        minutes = INTERVAL_MINUTES[interval]
        if minutes is None:
            raise ValueError(f"Unsupported interval: {interval}")
        if start.tzinfo is None:
            start = start.replace(tzinfo=IST)
        return start.astimezone(IST) + timedelta(minutes=minutes)
