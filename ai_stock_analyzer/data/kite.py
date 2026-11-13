from __future__ import annotations

import os
from datetime import date, datetime, time
from typing import Any, Mapping, Sequence

from ai_stock_analyzer.data.provider import (
    AuthenticationError,
    DataUnavailableError,
    MarketDataProvider,
    ProviderError,
    Quote,
    UnsupportedIntervalError,
)
from ai_stock_analyzer.market.bars import Bar, sort_bars
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.constants import DAILY_INTERVAL
from ai_stock_analyzer.market.instruments import Instrument
from ai_stock_analyzer.market.symbols import InstrumentSymbol


KITE_INTERVAL_MAP = {
    "1m": "minute",
    "3m": "3minute",
    "5m": "5minute",
    "15m": "15minute",
    "1d": "day",
}


def _ensure_ist(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.combine(value, time.min)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=IST)
    return moment.astimezone(IST)


class KiteProvider(MarketDataProvider):
    def __init__(self, client: Any, exchange: str = "NSE") -> None:
        self._client = client
        self._exchange = exchange.strip().upper()
        self._instruments_by_exchange: dict[str, tuple[Instrument, ...]] = {}

    @property
    def name(self) -> str:
        return "kite"

    @classmethod
    def from_credentials(cls, api_key: str, access_token: str) -> "KiteProvider":
        try:
            from kiteconnect import KiteConnect
        except ImportError as exc:
            raise ProviderError(
                "kiteconnect is not installed; install the optional 'kite' extra"
            ) from exc
        client = KiteConnect(api_key=api_key)
        client.set_access_token(access_token)
        return cls(client)

    @classmethod
    def from_env(cls) -> "KiteProvider":
        api_key = os.environ.get("KITE_API_KEY", "").strip()
        access_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip()
        if not api_key or not access_token:
            raise AuthenticationError(
                "Set KITE_API_KEY and KITE_ACCESS_TOKEN before using the Kite provider"
            )
        return cls.from_credentials(api_key, access_token)

    def _load_instruments(self, exchange: str) -> tuple[Instrument, ...]:
        normalized = exchange.strip().upper()
        if normalized in self._instruments_by_exchange:
            return self._instruments_by_exchange[normalized]
        try:
            rows = self._client.instruments(normalized)
        except Exception as exc:
            raise ProviderError(
                f"Kite instrument download failed for {normalized}: {exc}"
            ) from exc
        instruments: list[Instrument] = []
        for row in rows:
            if str(row.get("instrument_type", "")).upper() != "EQ":
                continue
            row_exchange = str(row.get("exchange", normalized)).upper()
            if row_exchange != normalized:
                continue
            tradingsymbol = row.get("tradingsymbol")
            if not tradingsymbol:
                continue
            try:
                symbol = InstrumentSymbol(str(tradingsymbol), normalized)
            except ValueError:
                continue
            token = row.get("instrument_token")
            instruments.append(
                Instrument(
                    symbol=symbol,
                    name=str(row.get("name", "")),
                    industry=str(row.get("segment", "")),
                    series=str(row.get("instrument_type", "EQ")),
                    isin=str(row["isin"]) if row.get("isin") else None,
                    instrument_token=int(token) if token is not None else None,
                )
            )
        result = tuple(instruments)
        self._instruments_by_exchange[normalized] = result
        return result

    def list_instruments(self, exchange: str = "NSE") -> list[Instrument]:
        return list(self._load_instruments(exchange))

    def _instrument_for(self, symbol: InstrumentSymbol) -> Instrument:
        for item in self._load_instruments(symbol.exchange):
            if item.symbol.tradingsymbol == symbol.tradingsymbol:
                return item
        raise DataUnavailableError(
            f"Kite instrument not found for {symbol.canonical}"
        )

    def _bar_start(self, value: object, interval: str) -> datetime:
        if isinstance(value, datetime):
            moment = value
        elif isinstance(value, date):
            moment = datetime.combine(value, time.min)
        else:
            moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        local = _ensure_ist(moment)
        if interval == DAILY_INTERVAL:
            return datetime.combine(local.date(), time.min, tzinfo=IST)
        return local

    def historical_bars(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        parsed = InstrumentSymbol.parse(symbol)
        if interval not in KITE_INTERVAL_MAP:
            raise UnsupportedIntervalError(f"Unsupported interval: {interval}")
        if start.tzinfo is None or end.tzinfo is None:
            raise ProviderError("Start and end must be timezone-aware")
        token = self._instrument_for(parsed).instrument_token
        if token is None:
            raise DataUnavailableError(
                f"No instrument token available for {parsed.canonical}"
            )
        try:
            rows: Sequence[Mapping[str, object]] = self._client.historical_data(
                token,
                start,
                end,
                KITE_INTERVAL_MAP[interval],
                continuous=False,
                oi=False,
            )
        except Exception as exc:
            raise ProviderError(
                f"Kite historical_data failed for {parsed.canonical}: {exc}"
            ) from exc
        bars: list[Bar] = []
        for row in rows:
            try:
                bars.append(
                    Bar(
                        symbol=parsed.canonical,
                        interval=interval,
                        start=self._bar_start(row["date"], interval),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0.0)),
                        open_interest=(
                            float(row["oi"]) if row.get("oi") is not None else None
                        ),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError(
                    f"Invalid Kite bar for {parsed.canonical}: {exc}"
                ) from exc
        return sort_bars(bars)

    def quote(self, symbol: str) -> Quote:
        parsed = InstrumentSymbol.parse(symbol)
        key = parsed.canonical
        try:
            payload = self._client.quote([key])
        except Exception as exc:
            raise ProviderError(f"Kite quote failed for {key}: {exc}") from exc
        data = payload.get(key)
        if not data:
            raise DataUnavailableError(f"Kite returned no quote for {key}")
        last_price = data.get("last_price")
        if last_price is None:
            raise DataUnavailableError(f"Kite quote for {key} has no last_price")
        timestamp = data.get("timestamp")
        moment = _ensure_ist(timestamp) if timestamp is not None else datetime.now(IST)
        net_change = data.get("net_change")
        change_percent = None
        if net_change is not None:
            previous = float(last_price) - float(net_change)
            if previous:
                change_percent = float(net_change) / previous * 100.0
        return Quote(
            symbol=key,
            last_price=float(last_price),
            timestamp=moment,
            volume=(
                float(data["volume"])
                if data.get("volume") is not None
                else None
            ),
            open_interest=(
                float(data["oi"]) if data.get("oi") is not None else None
            ),
            change=float(net_change) if net_change is not None else None,
            change_percent=change_percent,
        )
