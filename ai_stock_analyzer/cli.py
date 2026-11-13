from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from ai_stock_analyzer import __version__
from ai_stock_analyzer.data.feasibility import format_report, run_feasibility
from ai_stock_analyzer.data.fixtures import generate_universe_bars, load_bars
from ai_stock_analyzer.data.kite import KiteProvider
from ai_stock_analyzer.data.provider import (
    AuthenticationError,
    FakeProvider,
    ProviderError,
)
from ai_stock_analyzer.market.calendar import (
    CalendarCoverageError,
    NSECalendar,
    load_nse_holiday_data,
)
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.constants import INTERVAL_MINUTES
from ai_stock_analyzer.market.instruments import load_nifty50


def _today_ist() -> date:
    return datetime.now(IST).date()


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_feasibility_day(calendar: NSECalendar) -> date:
    today = _today_ist()
    if calendar.is_trading_day(today):
        return today
    return calendar.previous_trading_day(today)


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def _cmd_calendar(args: argparse.Namespace) -> int:
    calendar = NSECalendar()
    try:
        day = _parse_date(args.date) if args.date else _today_ist()
        is_open = calendar.is_trading_day(day)
        start = day if is_open else calendar.next_trading_day(day)
        days = []
        cursor = start
        for _ in range(args.days):
            days.append(cursor)
            cursor = calendar.next_trading_day(cursor)
        payload = {
            "date": day.isoformat(),
            "is_trading_day": is_open,
            "holiday": calendar.holiday_name(day),
            "special_session": (
                calendar.special_session(day).name
                if calendar.special_session(day)
                else None
            ),
            "session": (
                {
                    "open": calendar.session(day).open.isoformat(),
                    "close": calendar.session(day).close.isoformat(),
                }
                if is_open
                else None
            ),
            "upcoming": [item.isoformat() for item in days],
        }
    except (CalendarCoverageError, ValueError) as exc:
        _print_error(str(exc))
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    if is_open:
        session = calendar.session(day)
        print(f"{day.isoformat()} {day.strftime('%a')}: OPEN {session.open.strftime('%H:%M')}-{session.close.strftime('%H:%M')}")
    else:
        name = calendar.holiday_name(day)
        special = calendar.special_session(day)
        reason = name or (special.name if special else "weekend")
        print(f"{day.isoformat()} {day.strftime('%a')}: CLOSED ({reason})")
    print("Upcoming trading days:")
    for item in days:
        print(f"  {item.isoformat()} {item.strftime('%a')}")
    return 0


def _cmd_instruments(args: argparse.Namespace) -> int:
    universe = load_nifty50()
    payload = {
        "index": universe.index_name,
        "exchange": universe.exchange,
        "retrieved_at": universe.retrieved_at.isoformat(),
        "source": universe.source,
        "count": len(universe),
        "constituents": [
            {
                "symbol": item.tradingsymbol,
                "name": item.name,
                "industry": item.industry,
                "isin": item.isin,
            }
            for item in universe
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"{universe.index_name} ({len(universe)} constituents)")
    print(f"Source: {universe.source}")
    print(f"Retrieved: {universe.retrieved_at.isoformat()}")
    for item in universe:
        print(f"  {item.tradingsymbol:<12} {item.industry}")
    return 0


def _cmd_holidays(args: argparse.Namespace) -> int:
    try:
        data = load_nse_holiday_data(args.year)
    except CalendarCoverageError as exc:
        _print_error(str(exc))
        return 2
    payload = {
        "exchange": "NSE",
        "segment": "EQUITY",
        "year": data.year,
        "source": data.source,
        "retrieved_at": data.retrieved_at.isoformat(),
        "trading_holidays": [
            {"date": day.isoformat(), "name": name}
            for day, name in sorted(data.trading_holidays.items())
        ],
        "weekend_holidays": [
            {"date": day.isoformat(), "name": name}
            for day, name in sorted(data.weekend_holidays.items())
        ],
        "special_sessions": [
            {
                "date": item.day.isoformat(),
                "name": item.name,
                "regular_session": item.regular_session,
            }
            for item in sorted(
                data.special_sessions.values(), key=lambda value: value.day
            )
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"NSE equity holidays {data.year} ({len(data.trading_holidays)} weekday)")
    print(f"Source: {data.source}")
    print(f"Retrieved: {data.retrieved_at.isoformat()}")
    for day, name in sorted(data.trading_holidays.items()):
        print(f"  {day.isoformat()} {day.strftime('%a')}  {name}")
    if data.weekend_holidays:
        print("Weekend holidays:")
        for day, name in sorted(data.weekend_holidays.items()):
            print(f"  {day.isoformat()} {day.strftime('%a')}  {name}")
    if data.special_sessions:
        print("Special sessions:")
        for item in sorted(data.special_sessions.values(), key=lambda value: value.day):
            print(f"  {item.day.isoformat()} {item.day.strftime('%a')}  {item.name}")
    return 0


def _cmd_feasibility(args: argparse.Namespace) -> int:
    calendar = NSECalendar()
    try:
        day = _parse_date(args.date) if args.date else _default_feasibility_day(calendar)
        universe = load_nifty50()
        if args.provider == "fixtures":
            if args.fixtures_dir:
                bars = load_bars(Path(args.fixtures_dir) / "bars.json")
            elif calendar.is_trading_day(day):
                bars = generate_universe_bars(
                    universe,
                    day,
                    args.interval,
                    calendar=calendar,
                    seed=args.seed,
                )
            else:
                bars = {}
            provider = FakeProvider(universe.instruments, bars)
        else:
            provider = KiteProvider.from_env()
        report = run_feasibility(
            provider,
            universe,
            day=day,
            interval=args.interval,
            calendar=calendar,
            max_missing_ratio=args.max_missing_ratio,
            include_quotes=args.quotes,
        )
    except (
        AuthenticationError,
        CalendarCoverageError,
        OSError,
        ProviderError,
        ValueError,
    ) as exc:
        _print_error(str(exc))
        return 2
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        print(format_report(report))
    return 0 if report.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-stock-analyzer",
        description="AI-powered trading intelligence for Indian markets",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    calendar_parser = subparsers.add_parser(
        "calendar", help="Inspect NSE trading days and sessions"
    )
    calendar_parser.add_argument("--date", help="Date in YYYY-MM-DD; defaults to today IST")
    calendar_parser.add_argument("--days", type=int, default=10)
    calendar_parser.add_argument("--json", action="store_true")
    calendar_parser.set_defaults(func=_cmd_calendar)

    instruments_parser = subparsers.add_parser(
        "instruments", help="Show the NIFTY 50 instrument master"
    )
    instruments_parser.add_argument("--json", action="store_true")
    instruments_parser.set_defaults(func=_cmd_instruments)

    holidays_parser = subparsers.add_parser(
        "holidays", help="Show verified NSE holiday data"
    )
    holidays_parser.add_argument("--year", type=int, default=2026)
    holidays_parser.add_argument("--json", action="store_true")
    holidays_parser.set_defaults(func=_cmd_holidays)

    feasibility_parser = subparsers.add_parser(
        "feasibility", help="Check data coverage for the NIFTY 50 universe"
    )
    feasibility_parser.add_argument(
        "--provider", choices=("fixtures", "kite"), default="fixtures"
    )
    feasibility_parser.add_argument("--date", help="Date in YYYY-MM-DD")
    feasibility_parser.add_argument(
        "--interval", choices=tuple(INTERVAL_MINUTES), default="5m"
    )
    feasibility_parser.add_argument("--seed", type=int, default=7)
    feasibility_parser.add_argument("--fixtures-dir")
    feasibility_parser.add_argument("--max-missing-ratio", type=float, default=0.0)
    feasibility_parser.add_argument("--quotes", action="store_true")
    feasibility_parser.add_argument("--json", action="store_true")
    feasibility_parser.set_defaults(func=_cmd_feasibility)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        return 130
