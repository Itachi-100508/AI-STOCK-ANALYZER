import json
import unittest
from dataclasses import replace
from datetime import date, datetime

from ai_stock_analyzer.data.feasibility import (
    format_report,
    run_feasibility,
)
from ai_stock_analyzer.data.fixtures import generate_universe_bars
from ai_stock_analyzer.data.provider import FakeProvider, ProviderError
from ai_stock_analyzer.market.bars import Bar
from ai_stock_analyzer.market.calendar import NSECalendar
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.instruments import load_nifty50


class FailingHistoricalProvider(FakeProvider):
    def historical_bars(self, symbol, interval, start, end):
        raise ProviderError("historical endpoint unavailable")


class FailingInstrumentProvider(FakeProvider):
    def list_instruments(self, exchange="NSE"):
        raise ProviderError("instrument endpoint unavailable")


class FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = load_nifty50()

    def setUp(self):
        self.calendar = NSECalendar()
        self.day = date(2026, 11, 12)
        self.interval = "5m"
        self.bars = generate_universe_bars(
            self.universe, self.day, self.interval, self.calendar, seed=3
        )
        self.provider = FakeProvider(self.universe.instruments, self.bars)

    def run_report(self, provider=None, day=None, include_quotes=False):
        return run_feasibility(
            provider or self.provider,
            self.universe,
            day=day or self.day,
            interval=self.interval,
            calendar=self.calendar,
            include_quotes=include_quotes,
        )

    def test_complete_fixture_passes(self):
        report = self.run_report()
        self.assertTrue(report.passed)
        self.assertEqual(report.expected_symbols, 50)
        self.assertEqual(report.covered_symbols, 50)
        self.assertEqual(report.expected_bars_per_symbol, 75)
        self.assertEqual(report.total_expected_bars, 3750)
        self.assertEqual(report.total_received_bars, 3750)
        self.assertEqual(report.critical_failures, ())
        self.assertTrue(all(item.status == "ok" for item in report.symbols))

    def test_missing_instrument_fails(self):
        instruments = [
            item for item in self.universe.instruments if item.tradingsymbol != "RELIANCE"
        ]
        report = self.run_report(FakeProvider(instruments, self.bars))
        self.assertFalse(report.passed)
        self.assertEqual(report.covered_symbols, 49)
        self.assertTrue(
            any("missing 1 instruments" in item for item in report.critical_failures)
        )
        reliance = next(
            item for item in report.symbols if item.symbol == "NSE:RELIANCE"
        )
        self.assertEqual(reliance.status, "missing")

    def test_missing_bar_fails(self):
        bars = dict(self.bars)
        bars["NSE:RELIANCE"] = bars["NSE:RELIANCE"][1:]
        report = self.run_report(FakeProvider(self.universe.instruments, bars))
        self.assertFalse(report.passed)
        reliance = next(
            item for item in report.symbols if item.symbol == "NSE:RELIANCE"
        )
        self.assertEqual(reliance.missing_bars, 1)
        self.assertEqual(reliance.status, "partial")
        self.assertTrue(
            any("1/75 expected bars missing" in item for item in report.critical_failures)
        )

    def test_duplicate_bar_fails(self):
        bars = dict(self.bars)
        bars["NSE:RELIANCE"] = [
            bars["NSE:RELIANCE"][0],
            bars["NSE:RELIANCE"][0],
            *bars["NSE:RELIANCE"][1:],
        ]
        report = self.run_report(FakeProvider(self.universe.instruments, bars))
        self.assertFalse(report.passed)
        reliance = next(
            item for item in report.symbols if item.symbol == "NSE:RELIANCE"
        )
        self.assertEqual(reliance.duplicate_bars, 1)
        self.assertTrue(
            any("duplicate bars" in item for item in report.critical_failures)
        )

    def test_out_of_session_bar_fails(self):
        forged = object.__new__(Bar)
        object.__setattr__(forged, "symbol", "NSE:RELIANCE")
        object.__setattr__(forged, "interval", "5m")
        object.__setattr__(
            forged, "start", datetime(2026, 11, 12, 9, 16, tzinfo=IST)
        )
        object.__setattr__(forged, "open", 100.0)
        object.__setattr__(forged, "high", 101.0)
        object.__setattr__(forged, "low", 99.0)
        object.__setattr__(forged, "close", 100.5)
        object.__setattr__(forged, "volume", 1000.0)
        object.__setattr__(forged, "open_interest", None)
        bars = dict(self.bars)
        bars["NSE:RELIANCE"] = [*bars["NSE:RELIANCE"], forged]
        report = self.run_report(FakeProvider(self.universe.instruments, bars))
        self.assertFalse(report.passed)
        reliance = next(
            item for item in report.symbols if item.symbol == "NSE:RELIANCE"
        )
        self.assertEqual(reliance.out_of_session_bars, 1)
        self.assertTrue(
            any("out-of-session" in item for item in report.critical_failures)
        )

    def test_zero_volume_is_a_warning(self):
        bars = dict(self.bars)
        bars["NSE:RELIANCE"] = [
            replace(bars["NSE:RELIANCE"][0], volume=0),
            *bars["NSE:RELIANCE"][1:],
        ]
        report = self.run_report(FakeProvider(self.universe.instruments, bars))
        self.assertTrue(report.passed)
        self.assertTrue(any("zero-volume" in item for item in report.warnings))

    def test_non_trading_day_fails(self):
        report = self.run_report(day=date(2026, 11, 10))
        self.assertFalse(report.passed)
        self.assertFalse(report.is_trading_day)
        self.assertEqual(report.expected_bars_per_symbol, 0)
        self.assertEqual(report.total_expected_bars, 0)

    def test_historical_failure_is_reported(self):
        report = self.run_report(
            FailingHistoricalProvider(self.universe.instruments, self.bars)
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.covered_symbols, 0)
        self.assertEqual(len(report.critical_failures), 50)

    def test_instrument_failure_is_reported(self):
        report = self.run_report(
            FailingInstrumentProvider(self.universe.instruments, self.bars)
        )
        self.assertFalse(report.passed)
        self.assertEqual(report.symbols, ())
        self.assertIn("instrument list failed", report.critical_failures[0])

    def test_quote_failures_are_fatal_when_widespread(self):
        report = self.run_report(include_quotes=True)
        self.assertFalse(report.passed)
        self.assertTrue(any("quotes failed" in item for item in report.critical_failures))

    def test_report_is_json_serializable(self):
        report = self.run_report()
        payload = report.to_dict()
        self.assertTrue(json.loads(json.dumps(payload))["passed"])
        self.assertEqual(len(payload["symbols"]), 50)

    def test_format_report(self):
        text = format_report(self.run_report())
        self.assertIn("Status: PASS", text)
        self.assertIn("Provider: fake", text)
        text = format_report(self.run_report(day=date(2026, 11, 10)))
        self.assertIn("Status: FAIL", text)


if __name__ == "__main__":
    unittest.main()
