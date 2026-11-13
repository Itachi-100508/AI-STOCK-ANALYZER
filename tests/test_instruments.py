import unittest

from ai_stock_analyzer.market.instruments import load_nifty50


class Nifty50UniverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.universe = load_nifty50()

    def test_count_and_metadata(self):
        self.assertEqual(len(self.universe), 50)
        self.assertEqual(self.universe.index_name, "NIFTY 50")
        self.assertEqual(self.universe.exchange, "NSE")
        self.assertTrue(self.universe.source.startswith("https://www.niftyindices.com/"))

    def test_all_constituents_are_nse_equity(self):
        for instrument in self.universe:
            self.assertEqual(instrument.symbol.exchange, "NSE")
            self.assertEqual(instrument.series, "EQ")
            self.assertIsNotNone(instrument.isin)

    def test_unique_symbols_and_isins(self):
        symbols = self.universe.symbols
        self.assertEqual(len(symbols), len(set(symbols)))
        isins = [item.isin for item in self.universe]
        self.assertEqual(len(isins), len(set(isins)))

    def test_current_constituents(self):
        for symbol in ("RELIANCE", "TCS", "HDFCBANK", "BSE", "INDIGO", "TMPV"):
            with self.subTest(symbol=symbol):
                self.assertIsNotNone(self.universe.get(symbol))

    def test_get_accepts_canonical(self):
        instrument = self.universe.get("NSE:reliance")
        self.assertEqual(instrument.tradingsymbol, "RELIANCE")

    def test_require_raises_for_unknown(self):
        with self.assertRaises(KeyError):
            self.universe.require("NOTREAL")

    def test_missing_from(self):
        available = [symbol for symbol in self.universe.symbols if symbol != "TCS"]
        self.assertEqual(self.universe.missing_from(available), ["TCS"])

    def test_validate_is_clean(self):
        self.assertEqual(self.universe.validate(), [])


if __name__ == "__main__":
    unittest.main()
