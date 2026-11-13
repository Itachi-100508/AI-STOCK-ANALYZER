import tempfile
import unittest
from datetime import date
from pathlib import Path

from ai_stock_analyzer.data.fixtures import (
    dump_bars,
    generate_bars,
    generate_universe_bars,
    load_bars,
)
from ai_stock_analyzer.market.calendar import NSECalendar, NotATradingDayError
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.instruments import load_nifty50


class FixtureGenerationTests(unittest.TestCase):
    def setUp(self):
        self.calendar = NSECalendar()
        self.day = date(2026, 11, 12)
        self.universe = load_nifty50()

    def test_deterministic(self):
        first = generate_bars("RELIANCE", self.day, "5m", self.calendar, seed=11)
        second = generate_bars("RELIANCE", self.day, "5m", self.calendar, seed=11)
        self.assertEqual(first, second)

    def test_seed_changes_data(self):
        first = generate_bars("RELIANCE", self.day, "5m", self.calendar, seed=11)
        second = generate_bars("RELIANCE", self.day, "5m", self.calendar, seed=12)
        self.assertNotEqual([bar.close for bar in first], [bar.close for bar in second])

    def test_bar_count_and_quality(self):
        bars = generate_bars("RELIANCE", self.day, "5m", self.calendar)
        self.assertEqual(len(bars), 75)
        self.assertEqual(bars[0].start.hour, 9)
        self.assertEqual(bars[0].start.minute, 15)
        self.assertEqual(bars[-1].start.hour, 15)
        self.assertEqual(bars[-1].start.minute, 25)
        for bar in bars:
            self.assertGreaterEqual(bar.high, max(bar.open, bar.close))
            self.assertLessEqual(bar.low, min(bar.open, bar.close))
            self.assertGreater(bar.volume, 0)
            self.assertEqual(bar.start.tzinfo, IST)

    def test_daily_bar(self):
        bars = generate_bars("RELIANCE", self.day, "1d", self.calendar)
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].start.hour, 0)
        self.assertEqual(bars[0].start.minute, 0)

    def test_holiday_raises(self):
        with self.assertRaises(NotATradingDayError):
            generate_bars("RELIANCE", date(2026, 11, 10), "5m", self.calendar)

    def test_universe_generation(self):
        bars = generate_universe_bars(
            self.universe, self.day, "5m", self.calendar, seed=5
        )
        self.assertEqual(len(bars), 50)
        self.assertEqual(set(bars), set(self.universe.by_canonical))
        self.assertTrue(all(len(items) == 75 for items in bars.values()))

    def test_dump_and_load_round_trip(self):
        bars = generate_universe_bars(self.universe, self.day, "5m", self.calendar)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.json"
            dump_bars(path, bars)
            loaded = load_bars(path)
        self.assertEqual(set(loaded), set(bars))
        self.assertEqual(loaded["NSE:RELIANCE"], bars["NSE:RELIANCE"])


if __name__ == "__main__":
    unittest.main()
