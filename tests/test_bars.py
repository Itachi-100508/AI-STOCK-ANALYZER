import unittest
from datetime import datetime, timedelta

from ai_stock_analyzer.market.bars import (
    Bar,
    BarError,
    dedupe_bars,
    duplicate_starts,
    group_by_day,
    missing_starts,
    sort_bars,
    validate_bar_series,
)
from ai_stock_analyzer.market.clock import IST


def make_bar(minute=15, close=100.5, volume=1000, interval="5m", symbol="NSE:RELIANCE"):
    hour = 9 + minute // 60
    minute_part = minute % 60
    return Bar(
        symbol=symbol,
        interval=interval,
        start=datetime(2026, 11, 12, hour, minute_part, tzinfo=IST),
        open=100.0,
        high=max(101.0, close),
        low=min(99.0, close),
        close=close,
        volume=volume,
    )


class BarTests(unittest.TestCase):
    def test_valid_bar(self):
        bar = make_bar()
        self.assertEqual(bar.symbol, "NSE:RELIANCE")
        self.assertEqual(bar.end, datetime(2026, 11, 12, 9, 20, tzinfo=IST))
        self.assertEqual(bar.session_date.isoformat(), "2026-11-12")

    def test_symbol_is_canonicalized(self):
        bar = make_bar(symbol="reliance")
        self.assertEqual(bar.symbol, "NSE:RELIANCE")

    def test_naive_datetime_is_rejected(self):
        with self.assertRaises(BarError):
            Bar(
                symbol="RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 15),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )

    def test_out_of_session_bar_is_rejected(self):
        with self.assertRaises(BarError):
            Bar(
                symbol="RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 10, tzinfo=IST),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )

    def test_bar_beyond_close_is_rejected(self):
        with self.assertRaises(BarError):
            Bar(
                symbol="RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 15, 30, tzinfo=IST),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )

    def test_misaligned_bar_is_rejected(self):
        with self.assertRaises(BarError):
            Bar(
                symbol="RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 17, tzinfo=IST),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            )

    def test_invalid_ohlc_is_rejected(self):
        with self.assertRaises(BarError):
            Bar(
                symbol="RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 15, tzinfo=IST),
                open=100.0,
                high=99.5,
                low=98.0,
                close=100.5,
                volume=1000,
            )

    def test_negative_volume_is_rejected(self):
        with self.assertRaises(BarError):
            make_bar(volume=-1)

    def test_daily_bar(self):
        bar = Bar(
            symbol="RELIANCE",
            interval="1d",
            start=datetime(2026, 11, 12, 0, 0, tzinfo=IST),
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=100000,
        )
        self.assertTrue(bar.is_daily)
        self.assertEqual(bar.end, datetime(2026, 11, 12, 15, 30, tzinfo=IST))

    def test_round_trip(self):
        bar = make_bar()
        self.assertEqual(Bar.from_dict(bar.to_dict()), bar)

    def test_sort_dedupe_and_group(self):
        first = make_bar(15)
        second = make_bar(20, close=101.0)
        duplicate = make_bar(15, close=99.5)
        bars = [second, first, duplicate]
        self.assertEqual(sort_bars(bars)[0].start, first.start)
        self.assertEqual(duplicate_starts(bars), [first.start])
        self.assertEqual(len(dedupe_bars(bars, keep="last")), 2)
        self.assertEqual(group_by_day(bars)[first.session_date][0], first)

    def test_validate_series(self):
        first = make_bar(15)
        second = make_bar(20, close=101.0)
        self.assertEqual(validate_bar_series([first, second]), [])
        self.assertIn("Duplicate bar starts: 1", validate_bar_series([first, first]))
        self.assertIn(
            "Bars are not sorted by start time",
            validate_bar_series([second, first]),
        )

    def test_missing_starts(self):
        first = make_bar(15)
        second = make_bar(20, close=101.0)
        expected = [first.start, second.start, first.start + timedelta(minutes=15)]
        self.assertEqual(missing_starts([first, second], expected), [expected[-1]])


if __name__ == "__main__":
    unittest.main()
