from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from ai_stock_analyzer.market.bars import Bar, sort_bars
from ai_stock_analyzer.market.clock import IST
from ai_stock_analyzer.market.constants import INTERVAL_MINUTES
from ai_stock_analyzer.market.instruments import Instrument
from ai_stock_analyzer.market.symbols import canonical_symbol


class ProviderError(Exception):
    pass


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    pass


class DataUnavailableError(ProviderError):
    pass


class UnsupportedIntervalError(ProviderError):
    pass


@dataclass(frozen=True)
class Quote:
    symbol: str
    last_price: float
    timestamp: datetime
    volume: float | None = None
    open_interest: float | None = None
    change: float | None = None
    change_percent: float | None = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Quote timestamp must be timezone-aware")
        if not math.isfinite(self.last_price) or self.last_price <= 0:
            raise ValueError("Quote last_price must be finite and positive")
        for name in ("volume", "open_interest"):
            value = getattr(self, name)
            if value is not None and (
                not math.isfinite(value) or value < 0
            ):
                raise ValueError(f"Quote {name} must be finite and non-negative")
        for name in ("change", "change_percent"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"Quote {name} must be finite")
        object.__setattr__(self, "symbol", canonical_symbol(self.symbol))
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(IST))
        object.__setattr__(self, "last_price", float(self.last_price))
        if self.volume is not None:
            object.__setattr__(self, "volume", float(self.volume))
        if self.open_interest is not None:
            object.__setattr__(self, "open_interest", float(self.open_interest))


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_instruments(self, exchange: str = "NSE") -> list[Instrument]:
        raise NotImplementedError

    @abstractmethod
    def historical_bars(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        raise NotImplementedError

    @abstractmethod
    def quote(self, symbol: str) -> Quote:
        raise NotImplementedError


class FakeProvider(MarketDataProvider):
    def __init__(
        self,
        instruments: Iterable[Instrument],
        bars_by_symbol: Mapping[str, Iterable[Bar]] | None = None,
        quotes: Mapping[str, Quote] | None = None,
    ) -> None:
        self._instruments = tuple(instruments)
        self._bars: dict[str, list[Bar]] = {}
        for key, bars in (bars_by_symbol or {}).items():
            self._bars[canonical_symbol(key)] = sort_bars(bars)
        self._quotes = {
            canonical_symbol(key): value for key, value in (quotes or {}).items()
        }

    @property
    def name(self) -> str:
        return "fake"

    def list_instruments(self, exchange: str = "NSE") -> list[Instrument]:
        normalized = exchange.strip().upper()
        return [
            item for item in self._instruments if item.symbol.exchange == normalized
        ]

    def historical_bars(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        if interval not in INTERVAL_MINUTES:
            raise UnsupportedIntervalError(f"Unsupported interval: {interval}")
        if start.tzinfo is None or end.tzinfo is None:
            raise ProviderError("Start and end must be timezone-aware")
        key = canonical_symbol(symbol)
        selected = [
            bar
            for bar in self._bars.get(key, [])
            if bar.interval == interval and start <= bar.start <= end
        ]
        return sort_bars(selected)

    def quote(self, symbol: str) -> Quote:
        key = canonical_symbol(symbol)
        if key not in self._quotes:
            raise DataUnavailableError(f"No fake quote for {key}")
        return self._quotes[key]
