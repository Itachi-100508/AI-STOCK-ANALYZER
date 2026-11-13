import unittest
from datetime import date, datetime, time

from ai_stock_analyzer.market.calendar import (
    CalendarCoverageError,
    NSECalendar,
    NotATradingDayError,
)
from ai_stock_analyzer.market.clock import IST


class NSECalendarTests(unittest.TestCase):
    def setUp(self):
        self.calendar = NSECalendar()

    def test_weekend_is_closed(self):
        self.assertTrue(self.calendar.is_weekend(date(2026, 11, 14)))
        self.assertFalse(self.calendar.is_trading_day(date(2026, 11, 14)))
        self.assertFalse(self.calendar.is_trading_day(date(2026, 11, 15)))

    def test_verified_holidays_are_closed(self):
        holidays = [
            date(2026, 1, 15),
            date(2026, 1, 26),
            date(2026, 3, 3),
            date(2026, 10, 2),
            date(2026, 11, 10),
            date(2026, 12, 25),
        ]
        for day in holidays:
            with self.subTest(day=day):
                self.assertFalse(self.calendar.is_trading_day(day))
                self.assertIsNotNone(self.calendar.holiday_name(day))

    def test_january_fifteenth_late_holiday(self):
        day = date(2026, 1, 15)
        self.assertFalse(self.calendar.is_trading_day(day))
        self.assertIn("Maharashtra", self.calendar.holiday_name(day))

    def test_august_twenty_six_is_trading_day(self):
        self.assertTrue(self.calendar.is_trading_day(date(2026, 8, 26)))

    def test_regular_trading_day_session(self):
        day = date(2026, 11, 12)
        self.assertTrue(self.calendar.is_trading_day(day))
        session = self.calendar.session(day)
        self.assertEqual(session.open, datetime(2026, 11, 12, 9, 15, tzinfo=IST))
        self.assertEqual(session.close, datetime(2026, 11, 12, 15, 30, tzinfo=IST))

    def test_muhurat_session_is_not_regular(self):
        day = date(2026, 11, 8)
        self.assertFalse(self.calendar.is_trading_day(day))
        self.assertEqual(self.calendar.special_session(day).name, "Muhurat Trading")

    def test_unverified_year_raises(self):
        with self.assertRaises(CalendarCoverageError):
            self.calendar.is_trading_day(date(2027, 1, 4))

    def test_allow_unverified_years(self):
        calendar = NSECalendar(allow_unverified_years=True)
        self.assertTrue(calendar.is_trading_day(date(2027, 1, 4)))
        self.assertFalse(calendar.is_trading_day(date(2027, 1, 2)))

    def test_next_trading_day_skips_holiday(self):
        self.assertEqual(
            self.calendar.next_trading_day(date(2026, 11, 9)),
            date(2026, 11, 11),
        )

    def test_previous_trading_day_skips_holiday(self):
        self.assertEqual(
            self.calendar.previous_trading_day(date(2026, 11, 11)),
            date(2026, 11, 9),
        )

    def test_trading_days_range(self):
        days = self.calendar.trading_days(date(2026, 11, 6), date(2026, 11, 12))
        self.assertEqual(
            days,
            [
                date(2026, 11, 6),
                date(2026, 11, 9),
                date(2026, 11, 11),
                date(2026, 11, 12),
            ],
        )

    def test_expected_bar_counts(self):
        self.assertEqual(self.calendar.expected_bar_count("1m"), 375)
        self.assertEqual(self.calendar.expected_bar_count("3m"), 125)
        self.assertEqual(self.calendar.expected_bar_count("5m"), 75)
        self.assertEqual(self.calendar.expected_bar_count("15m"), 25)
        self.assertEqual(self.calendar.expected_bar_count("1d"), 1)

    def test_session_bar_starts(self):
        day = date(2026, 11, 12)
        starts = self.calendar.session_bar_starts(day, "5m")
        self.assertEqual(len(starts), 75)
        self.assertEqual(starts[0], datetime(2026, 11, 12, 9, 15, tzinfo=IST))
        self.assertEqual(starts[-1], datetime(2026, 11, 12, 15, 25, tzinfo=IST))

    def test_daily_bar_start(self):
        starts = self.calendar.session_bar_starts(date(2026, 11, 12), "1d")
        self.assertEqual(starts, [datetime(2026, 11, 12, 0, 0, tzinfo=IST)])

    def test_holiday_bar_starts_raise(self):
        with self.assertRaises(NotATradingDayError):
            self.calendar.session_bar_starts(date(2026, 11, 10), "5m")

    def test_is_session_bar_start(self):
        day = date(2026, 11, 12)
        self.assertTrue(
            self.calendar.is_session_bar_start(
                day, datetime(2026, 11, 12, 9, 15, tzinfo=IST), "5m"
            )
        )
        self.assertFalse(
            self.calendar.is_session_bar_start(
                day, datetime(2026, 11, 12, 9, 17, tzinfo=IST), "5m"
            )
        )
        self.assertFalse(
            self.calendar.is_session_bar_start(
                day, datetime(2026, 11, 12, 15, 30, tzinfo=IST), "5m"
            )
        )
        self.assertFalse(
            self.calendar.is_session_bar_start(
                date(2026, 11, 10), datetime(2026, 11, 10, 9, 15, tzinfo=IST), "5m"
            )
        )

    def test_bar_close(self):
        start = datetime(2026, 11, 12, 9, 15, tzinfo=IST)
        self.assertEqual(
            self.calendar.bar_close(start, "5m"),
            datetime(2026, 11, 12, 9, 20, tzinfo=IST),
        )
        self.assertEqual(
            self.calendar.bar_close(start, "1d"),
            datetime(2026, 11, 12, 15, 30, tzinfo=IST),
        )


if __name__ == "__main__":
    unittest.main()
