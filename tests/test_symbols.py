import unittest

from ai_stock_analyzer.market.symbols import (
    InstrumentSymbol,
    SymbolError,
    canonical_symbol,
)


class InstrumentSymbolTests(unittest.TestCase):
    def test_canonical_and_provider_mappings(self):
        symbol = InstrumentSymbol("reliance")
        self.assertEqual(symbol.tradingsymbol, "RELIANCE")
        self.assertEqual(symbol.exchange, "NSE")
        self.assertEqual(symbol.canonical, "NSE:RELIANCE")
        self.assertEqual(
            symbol.to_kite(), {"exchange": "NSE", "tradingsymbol": "RELIANCE"}
        )
        self.assertEqual(symbol.to_yahoo(), "RELIANCE.NS")

    def test_bse_mapping(self):
        symbol = InstrumentSymbol("500325", "BSE")
        self.assertEqual(symbol.canonical, "BSE:500325")
        self.assertEqual(symbol.to_yahoo(), "500325.BO")

    def test_special_characters(self):
        self.assertEqual(InstrumentSymbol("M&M").tradingsymbol, "M&M")
        self.assertEqual(InstrumentSymbol("BAJAJ-AUTO").tradingsymbol, "BAJAJ-AUTO")

    def test_yahoo_url_encodes_special_characters(self):
        url = InstrumentSymbol("M&M").yahoo_chart_url()
        self.assertTrue(url.endswith("/M%26M.NS"))

    def test_parse_canonical(self):
        symbol = InstrumentSymbol.parse("NSE:TCS")
        self.assertEqual(symbol.canonical, "NSE:TCS")
        self.assertEqual(canonical_symbol("tcs"), "NSE:TCS")

    def test_invalid_symbols(self):
        for value in ("", " ", "AB CD", "AB.C", "A:B", "-ABC"):
            with self.subTest(value=value):
                with self.assertRaises(SymbolError):
                    InstrumentSymbol(value)

    def test_invalid_exchange(self):
        with self.assertRaises(SymbolError):
            InstrumentSymbol("RELIANCE", "NYSE")


if __name__ == "__main__":
    unittest.main()
