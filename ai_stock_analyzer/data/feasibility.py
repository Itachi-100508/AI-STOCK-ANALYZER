from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Sequence

from ai_stock_analyzer.data.provider import MarketDataProvider, ProviderError
from ai_stock_analyzer.market.bars import (
    Bar,
    duplicate_starts,
    sort_bars,
    validate_bar_series,
)
from ai_stock_analyzer.market.calendar import NSECalendar
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.constants import DAILY_INTERVAL, INTERVAL_MINUTES
from ai_stock_analyzer.market.instruments import Nifty50Universe
from ai_stock_analyzer.market.symbols import canonical_symbol


@dataclass(frozen=True)
class SymbolCoverage:
    symbol: str
    status: str
    expected_bars: int
    received_bars: int
    unique_bars: int
    missing_bars: int
    duplicate_bars: int
    extra_bars: int
    out_of_session_bars: int
    zero_volume_bars: int
    issues: tuple[str, ...] = ()
    validation_issues: tuple[str, ...] = ()
    first_bar: datetime | None = None
    last_bar: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "status": self.status,
            "expected_bars": self.expected_bars,
            "received_bars": self.received_bars,
            "unique_bars": self.unique_bars,
            "missing_bars": self.missing_bars,
            "duplicate_bars": self.duplicate_bars,
            "extra_bars": self.extra_bars,
            "out_of_session_bars": self.out_of_session_bars,
            "zero_volume_bars": self.zero_volume_bars,
            "issues": list(self.issues),
            "validation_issues": list(self.validation_issues),
            "first_bar": self.first_bar.isoformat() if self.first_bar else None,
            "last_bar": self.last_bar.isoformat() if self.last_bar else None,
        }


@dataclass(frozen=True)
class FeasibilityReport:
    provider: str
    day: date
    interval: str
    is_trading_day: bool
    expected_symbols: int
    covered_symbols: int
    expected_bars_per_symbol: int
    total_expected_bars: int
    total_received_bars: int
    critical_failures: tuple[str, ...]
    warnings: tuple[str, ...]
    symbols: tuple[SymbolCoverage, ...]
    generated_at: datetime

    @property
    def passed(self) -> bool:
        return not self.critical_failures

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "day": self.day.isoformat(),
            "interval": self.interval,
            "is_trading_day": self.is_trading_day,
            "expected_symbols": self.expected_symbols,
            "covered_symbols": self.covered_symbols,
            "expected_bars_per_symbol": self.expected_bars_per_symbol,
            "total_expected_bars": self.total_expected_bars,
            "total_received_bars": self.total_received_bars,
            "passed": self.passed,
            "critical_failures": list(self.critical_failures),
            "warnings": list(self.warnings),
            "symbols": [item.to_dict() for item in self.symbols],
            "generated_at": self.generated_at.isoformat(),
        }


def _day_bounds(day: date, interval: str, calendar: NSECalendar) -> tuple[datetime, datetime]:
    if interval == DAILY_INTERVAL:
        start = datetime.combine(day, time.min, tzinfo=IST)
    else:
        start = calendar.session_open(day)
    end = datetime.combine(day, time.max, tzinfo=IST)
    return start, end


def _coverage_for_symbol(
    provider: MarketDataProvider,
    symbol: str,
    day: date,
    interval: str,
    expected_starts: Sequence[datetime],
    calendar: NSECalendar,
) -> SymbolCoverage:
    try:
        bars = provider.historical_bars(symbol, interval, *_day_bounds(day, interval, calendar))
    except ProviderError as exc:
        return SymbolCoverage(
            symbol=canonical_symbol(symbol),
            status="error",
            expected_bars=len(expected_starts),
            received_bars=0,
            unique_bars=0,
            missing_bars=len(expected_starts),
            duplicate_bars=0,
            extra_bars=0,
            out_of_session_bars=0,
            zero_volume_bars=0,
            issues=(str(exc),),
        )

    day_bars = sort_bars(
        bar
        for bar in bars
        if bar.interval == interval and bar.session_date == day
    )
    expected_set = set(expected_starts)
    starts = [bar.start for bar in day_bars]
    unique_starts = set(starts)
    duplicates = duplicate_starts(day_bars)
    missing = [start for start in expected_starts if start not in unique_starts]
    extra = [start for start in unique_starts if start not in expected_set]
    out_of_session = [
        bar.start
        for bar in day_bars
        if not calendar.is_session_bar_start(day, bar.start, interval)
    ]
    zero_volume = [bar for bar in day_bars if bar.volume == 0]
    series_issues = validate_bar_series(day_bars, symbol=symbol, interval=interval)
    issues = list(series_issues)
    if missing:
        issues.append(f"missing {len(missing)} expected bars")
    if extra:
        issues.append(f"{len(extra)} unexpected bars")
    if out_of_session:
        issues.append(f"{len(out_of_session)} out-of-session bars")
    if duplicates:
        issues.append(f"{len(duplicates)} duplicate bars")

    if not day_bars:
        status = "missing"
    elif issues:
        status = "partial"
    else:
        status = "ok"

    return SymbolCoverage(
        symbol=canonical_symbol(symbol),
        status=status,
        expected_bars=len(expected_starts),
        received_bars=len(day_bars),
        unique_bars=len(unique_starts),
        missing_bars=len(missing),
        duplicate_bars=len(duplicates),
        extra_bars=len(extra),
        out_of_session_bars=len(out_of_session),
        zero_volume_bars=len(zero_volume),
        issues=tuple(issues),
        validation_issues=tuple(series_issues),
        first_bar=day_bars[0].start if day_bars else None,
        last_bar=day_bars[-1].start if day_bars else None,
    )


def run_feasibility(
    provider: MarketDataProvider,
    universe: Nifty50Universe,
    day: date,
    interval: str,
    calendar: NSECalendar | None = None,
    max_missing_ratio: float = 0.0,
    include_quotes: bool = False,
) -> FeasibilityReport:
    if interval not in INTERVAL_MINUTES:
        raise ValueError(f"Unsupported interval: {interval}")
    if not 0.0 <= max_missing_ratio <= 1.0:
        raise ValueError("max_missing_ratio must be between 0 and 1")
    calendar = calendar or NSECalendar()
    generated_at = datetime.now(IST)

    if not calendar.is_trading_day(day):
        return FeasibilityReport(
            provider=provider.name,
            day=day,
            interval=interval,
            is_trading_day=False,
            expected_symbols=len(universe),
            covered_symbols=0,
            expected_bars_per_symbol=0,
            total_expected_bars=0,
            total_received_bars=0,
            critical_failures=(
                f"{day.isoformat()} is not a regular NSE trading day",
            ),
            warnings=(),
            symbols=(),
            generated_at=generated_at,
        )

    expected_starts = calendar.session_bar_starts(day, interval)
    expected_count = len(expected_starts)
    critical: list[str] = []
    warnings: list[str] = []

    try:
        instruments = provider.list_instruments(universe.exchange)
    except ProviderError as exc:
        return FeasibilityReport(
            provider=provider.name,
            day=day,
            interval=interval,
            is_trading_day=True,
            expected_symbols=len(universe),
            covered_symbols=0,
            expected_bars_per_symbol=expected_count,
            total_expected_bars=expected_count * len(universe),
            total_received_bars=0,
            critical_failures=(f"instrument list failed: {exc}",),
            warnings=(),
            symbols=(),
            generated_at=generated_at,
        )

    available = {
        item.tradingsymbol: item
        for item in instruments
        if item.symbol.exchange == universe.exchange
    }
    missing_instruments = universe.missing_from(available)
    if missing_instruments:
        critical.append(
            f"missing {len(missing_instruments)} instruments: "
            + ", ".join(missing_instruments[:10])
        )

    coverage: list[SymbolCoverage] = []
    for instrument in universe:
        if instrument.tradingsymbol not in available:
            coverage.append(
                SymbolCoverage(
                    symbol=instrument.canonical,
                    status="missing",
                    expected_bars=expected_count,
                    received_bars=0,
                    unique_bars=0,
                    missing_bars=expected_count,
                    duplicate_bars=0,
                    extra_bars=0,
                    out_of_session_bars=0,
                    zero_volume_bars=0,
                    issues=("instrument not available from provider",),
                )
            )
            continue
        item = _coverage_for_symbol(
            provider,
            instrument.tradingsymbol,
            day,
            interval,
            expected_starts,
            calendar,
        )
        coverage.append(item)
        if item.status == "error":
            critical.append(f"{item.symbol}: {item.issues[0]}")
            continue
        if item.received_bars == 0:
            critical.append(f"{item.symbol}: no bars returned")
            continue
        if expected_count and item.missing_bars / expected_count > max_missing_ratio:
            critical.append(
                f"{item.symbol}: {item.missing_bars}/{expected_count} expected bars missing"
            )
        if item.duplicate_bars:
            critical.append(f"{item.symbol}: {item.duplicate_bars} duplicate bars")
        if item.extra_bars:
            critical.append(f"{item.symbol}: {item.extra_bars} unexpected bars")
        if item.out_of_session_bars:
            critical.append(
                f"{item.symbol}: {item.out_of_session_bars} out-of-session bars"
            )
        for issue in item.validation_issues:
            if issue == "No bars" or issue.startswith("Duplicate bar starts"):
                continue
            critical.append(f"{item.symbol}: {issue}")
        if item.zero_volume_bars:
            warnings.append(
                f"{item.symbol}: {item.zero_volume_bars} zero-volume bars"
            )

    if include_quotes:
        quote_failures = 0
        for instrument in universe:
            try:
                provider.quote(instrument.tradingsymbol)
            except ProviderError as exc:
                quote_failures += 1
                warnings.append(f"{instrument.canonical}: quote failed: {exc}")
        if quote_failures > len(universe) // 2:
            critical.append(
                f"{quote_failures}/{len(universe)} quotes failed"
            )

    covered_symbols = sum(1 for item in coverage if item.received_bars > 0)
    return FeasibilityReport(
        provider=provider.name,
        day=day,
        interval=interval,
        is_trading_day=True,
        expected_symbols=len(universe),
        covered_symbols=covered_symbols,
        expected_bars_per_symbol=expected_count,
        total_expected_bars=expected_count * len(universe),
        total_received_bars=sum(item.received_bars for item in coverage),
        critical_failures=tuple(critical),
        warnings=tuple(warnings),
        symbols=tuple(coverage),
        generated_at=generated_at,
    )


def format_report(report: FeasibilityReport, max_lines: int = 20) -> str:
    lines = [
        "AI Stock Analyzer - Data Feasibility",
        f"Provider: {report.provider}",
        f"Day: {report.day.isoformat()}",
        f"Trading day: {'yes' if report.is_trading_day else 'no'}",
        f"Interval: {report.interval}",
        f"Expected symbols: {report.expected_symbols}",
        f"Covered symbols: {report.covered_symbols}",
        f"Expected bars/symbol: {report.expected_bars_per_symbol}",
        f"Total expected bars: {report.total_expected_bars}",
        f"Total received bars: {report.total_received_bars}",
        f"Critical failures: {len(report.critical_failures)}",
        f"Warnings: {len(report.warnings)}",
        f"Status: {'PASS' if report.passed else 'FAIL'}",
    ]
    if report.critical_failures:
        lines.append("")
        lines.append("Critical failures:")
        for item in report.critical_failures[:max_lines]:
            lines.append(f"  - {item}")
        remaining = len(report.critical_failures) - max_lines
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for item in report.warnings[:max_lines]:
            lines.append(f"  - {item}")
        remaining = len(report.warnings) - max_lines
        if remaining > 0:
            lines.append(f"  ... and {remaining} more")
    return "\n".join(lines)
