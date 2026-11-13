import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from ai_stock_analyzer.cli import main


class CLITests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_feasibility_fixtures_passes(self):
        code, output, _ = self.run_cli(
            ["feasibility", "--provider", "fixtures", "--date", "2026-11-12"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Status: PASS", output)

    def test_feasibility_json(self):
        code, output, _ = self.run_cli(
            [
                "feasibility",
                "--provider",
                "fixtures",
                "--date",
                "2026-11-12",
                "--interval",
                "15m",
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["interval"], "15m")

    def test_feasibility_on_holiday_fails(self):
        code, output, _ = self.run_cli(
            ["feasibility", "--provider", "fixtures", "--date", "2026-11-10"]
        )
        self.assertEqual(code, 1)
        self.assertIn("Status: FAIL", output)

    def test_feasibility_invalid_date(self):
        code, _, error = self.run_cli(
            ["feasibility", "--provider", "fixtures", "--date", "not-a-date"]
        )
        self.assertEqual(code, 2)
        self.assertIn("error:", error)

    def test_calendar_holiday(self):
        code, output, _ = self.run_cli(["calendar", "--date", "2026-11-10"])
        self.assertEqual(code, 0)
        self.assertIn("CLOSED", output)
        self.assertIn("Diwali", output)

    def test_calendar_unverified_year(self):
        code, _, error = self.run_cli(["calendar", "--date", "2027-01-04"])
        self.assertEqual(code, 2)
        self.assertIn("No verified NSE holiday data", error)

    def test_instruments(self):
        code, output, _ = self.run_cli(["instruments"])
        self.assertEqual(code, 0)
        self.assertIn("50 constituents", output)
        self.assertIn("RELIANCE", output)

    def test_holidays(self):
        code, output, _ = self.run_cli(["holidays", "--year", "2026"])
        self.assertEqual(code, 0)
        self.assertIn("16 weekday", output)
        self.assertIn("2026-01-15", output)
        self.assertIn("Muhurat Trading", output)

    def test_holidays_unverified_year(self):
        code, _, error = self.run_cli(["holidays", "--year", "2027"])
        self.assertEqual(code, 2)
        self.assertIn("No verified NSE holiday data", error)


if __name__ == "__main__":
    unittest.main()
