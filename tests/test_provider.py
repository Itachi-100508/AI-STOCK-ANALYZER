import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from ai_stock_analyzer.data.kite import KiteProvider
from ai_stock_analyzer.data.provider import (
    AuthenticationError,
    DataUnavailableError,
    FakeProvider,
    ProviderError,
    Quote,
    UnsupportedIntervalError,
)
from ai_stock_analyzer.market.bars import Bar
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.instruments import Instrument
from ai_stock_analyzer.market.symbols import InstrumentSymbol


class FakeKiteClient:
    def __init__(self, instruments, candles, quotes=None):
        self._instruments = instruments
        self._candles = candles
        self._quotes = quotes or {}
        self.calls = []

    def instruments(self, exchange=None):
        if exchange is None:
            return list(self._instruments)
        return [row for row in self._instruments if row["exchange"] == exchange]

    def historical_data(self, token, start, end, interval, continuous=False, oi=False):
        self.calls.append((token, start, end, interval, continuous, oi))
        return list(self._candles.get(token, []))

    def quote(self, keys):
        return {key: self._quotes[key] for key in keys}


def kite_instruments():
    return [
        {
            "instrument_token": 1,
            "tradingsymbol": "RELIANCE",
            "name": "Reliance Industries",
            "exchange": "NSE",
            "instrument_type": "EQ",
            "segment": "NSE",
            "isin": "INE002A01018",
        },
        {
            "instrument_token": 2,
            "tradingsymbol": "NIFTY26NOV25000CE",
            "name": "NIFTY",
            "exchange": "NSE",
            "instrument_type": "CE",
            "segment": "NFO-OPT",
        },
        {
            "instrument_token": 3,
            "tradingsymbol": "NIFTY26NOVFUT",
            "name": "NIFTY",
            "exchange": "NSE",
            "instrument_type": "FUT",
            "segment": "NFO-FUT",
        },
    ]


def candle(minute, close=100.5):
    return {
        "date": datetime(2026, 11, 12, 9, minute),
        "open": 100.0,
        "high": max(101.0, close),
        "low": min(99.0, close),
        "close": close,
        "volume": 1000,
    }


class FakeProviderTests(unittest.TestCase):
    def setUp(self):
        self.instrument = Instrument(
            symbol=InstrumentSymbol("RELIANCE"), name="Reliance", isin="INE002A01018"
        )
        self.bars = [
            Bar(
                symbol="NSE:RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 15, tzinfo=IST),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=1000,
            ),
            Bar(
                symbol="NSE:RELIANCE",
                interval="5m",
                start=datetime(2026, 11, 12, 9, 20, tzinfo=IST),
                open=100.5,
                high=102.0,
                low=100.0,
                close=101.5,
                volume=1200,
            ),
        ]
        self.quote = Quote(
            symbol="NSE:RELIANCE",
            last_price=100.5,
            timestamp=datetime(2026, 11, 12, 9, 21, tzinfo=IST),
            volume=5000,
        )
        self.provider = FakeProvider(
            [self.instrument], {"RELIANCE": self.bars}, {"RELIANCE": self.quote}
        )

    def test_list_instruments(self):
        self.assertEqual(self.provider.list_instruments("NSE"), [self.instrument])
        self.assertEqual(self.provider.list_instruments("BSE"), [])

    def test_historical_bars_filters(self):
        start = datetime(2026, 11, 12, 9, 0, tzinfo=IST)
        end = datetime(2026, 11, 12, 9, 30, tzinfo=IST)
        self.assertEqual(
            self.provider.historical_bars("RELIANCE", "5m", start, end), self.bars
        )
        self.assertEqual(
            self.provider.historical_bars("RELIANCE", "15m", start, end), []
        )

    def test_historical_bars_requires_aware_range(self):
        with self.assertRaises(ProviderError):
            self.provider.historical_bars(
                "RELIANCE", "5m", datetime(2026, 11, 12, 9, 0), datetime.now()
            )

    def test_unsupported_interval(self):
        with self.assertRaises(UnsupportedIntervalError):
            self.provider.historical_bars(
                "RELIANCE",
                "2m",
                datetime(2026, 11, 12, 9, 0, tzinfo=IST),
                datetime(2026, 11, 12, 9, 30, tzinfo=IST),
            )

    def test_quote(self):
        self.assertEqual(self.provider.quote("RELIANCE"), self.quote)

    def test_missing_quote(self):
        with self.assertRaises(DataUnavailableError):
            self.provider.quote("TCS")


class KiteProviderTests(unittest.TestCase):
    def setUp(self):
        self.candles = {
            1: [candle(15), candle(20, close=101.5)],
        }
        self.client = FakeKiteClient(kite_instruments(), self.candles)
        self.provider = KiteProvider(self.client)

    def test_list_instruments_filters_equity(self):
        instruments = self.provider.list_instruments("NSE")
        self.assertEqual([item.tradingsymbol for item in instruments], ["RELIANCE"])
        self.assertEqual(instruments[0].instrument_token, 1)

    def test_historical_bars(self):
        bars = self.provider.historical_bars(
            "NSE:RELIANCE",
            "5m",
            datetime(2026, 11, 12, 9, 0, tzinfo=IST),
            datetime(2026, 11, 12, 9, 30, tzinfo=IST),
        )
        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0].start, datetime(2026, 11, 12, 9, 15, tzinfo=IST))
        self.assertEqual(bars[0].symbol, "NSE:RELIANCE")
        self.assertEqual(self.client.calls[0][3], "5minute")

    def test_aware_timestamp_is_converted_to_ist(self):
        self.candles[1] = [
            {
                "date": datetime(2026, 11, 12, 3, 45, tzinfo=timezone.utc),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000,
            }
        ]
        bars = self.provider.historical_bars(
            "NSE:RELIANCE",
            "5m",
            datetime(2026, 11, 12, 9, 0, tzinfo=IST),
            datetime(2026, 11, 12, 9, 30, tzinfo=IST),
        )
        self.assertEqual(bars[0].start, datetime(2026, 11, 12, 9, 15, tzinfo=IST))

    def test_daily_bar_is_normalized_to_midnight(self):
        self.candles[1] = [
            {
                "date": date(2026, 11, 12),
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000,
            }
        ]
        bars = self.provider.historical_bars(
            "NSE:RELIANCE",
            "1d",
            datetime(2026, 11, 12, 0, 0, tzinfo=IST),
            datetime(2026, 11, 12, 23, 59, tzinfo=IST),
        )
        self.assertEqual(bars[0].start, datetime(2026, 11, 12, 0, 0, tzinfo=IST))

    def test_unsupported_interval(self):
        with self.assertRaises(UnsupportedIntervalError):
            self.provider.historical_bars(
                "NSE:RELIANCE",
                "2m",
                datetime(2026, 11, 12, 9, 0, tzinfo=IST),
                datetime(2026, 11, 12, 9, 30, tzinfo=IST),
            )

    def test_missing_instrument_token(self):
        with self.assertRaises(DataUnavailableError):
            self.provider.historical_bars(
                "NSE:TCS",
                "5m",
                datetime(2026, 11, 12, 9, 0, tzinfo=IST),
                datetime(2026, 11, 12, 9, 30, tzinfo=IST),
            )

    def test_quote(self):
        timestamp = datetime(2026, 11, 12, 9, 21, tzinfo=IST)
        self.client._quotes = {
            "NSE:RELIANCE": {
                "last_price": 100.0,
                "timestamp": timestamp,
                "volume": 5000,
                "oi": 0,
                "net_change": 2.0,
            }
        }
        quote = self.provider.quote("RELIANCE")
        self.assertEqual(quote.last_price, 100.0)
        self.assertEqual(quote.timestamp, timestamp)
        self.assertAlmostEqual(quote.change_percent, 2.0 / 98.0 * 100.0)

    def test_from_env_requires_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AuthenticationError):
                KiteProvider.from_env()

    def test_read_only_surface(self):
        self.assertFalse(hasattr(self.provider, "place_order"))
        self.assertFalse(hasattr(self.provider, "modify_order"))
        self.assertFalse(hasattr(self.provider, "cancel_order"))


if __name__ == "__main__":
    unittest.main()
