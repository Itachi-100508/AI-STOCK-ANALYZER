from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote


NSE_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9&\-]{0,19}$")
SUPPORTED_EXCHANGES = frozenset({"NSE", "BSE"})
YAHOO_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}


class SymbolError(ValueError):
    pass


@dataclass(frozen=True)
class InstrumentSymbol:
    tradingsymbol: str
    exchange: str = "NSE"

    def __post_init__(self) -> None:
        symbol = self.tradingsymbol.strip().upper()
        exchange = self.exchange.strip().upper()
        if exchange not in SUPPORTED_EXCHANGES:
            raise SymbolError(f"Unsupported exchange: {self.exchange}")
        if not NSE_SYMBOL_PATTERN.fullmatch(symbol):
            raise SymbolError(f"Invalid NSE tradingsymbol: {self.tradingsymbol}")
        object.__setattr__(self, "tradingsymbol", symbol)
        object.__setattr__(self, "exchange", exchange)

    @property
    def canonical(self) -> str:
        return f"{self.exchange}:{self.tradingsymbol}"

    @classmethod
    def parse(cls, value: str, default_exchange: str = "NSE") -> "InstrumentSymbol":
        raw = value.strip()
        if ":" in raw:
            exchange, symbol = raw.split(":", 1)
        else:
            exchange, symbol = default_exchange, raw
        return cls(tradingsymbol=symbol, exchange=exchange)

    def to_kite(self) -> dict[str, str]:
        return {"exchange": self.exchange, "tradingsymbol": self.tradingsymbol}

    def to_yahoo(self) -> str:
        return f"{self.tradingsymbol}{YAHOO_SUFFIX[self.exchange]}"

    def yahoo_chart_url(self) -> str:
        encoded = quote(self.to_yahoo(), safe="")
        return f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"

    def __str__(self) -> str:
        return self.canonical


def canonical_symbol(value: str, default_exchange: str = "NSE") -> str:
    return InstrumentSymbol.parse(value, default_exchange=default_exchange).canonical
