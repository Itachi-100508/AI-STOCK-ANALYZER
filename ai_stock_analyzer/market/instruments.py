from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from importlib import resources
from typing import Iterable, Mapping

from .symbols import InstrumentSymbol, SymbolError


class UniverseError(ValueError):
    pass


@dataclass(frozen=True)
class Instrument:
    symbol: InstrumentSymbol
    name: str
    industry: str = ""
    series: str = "EQ"
    isin: str | None = None
    instrument_token: int | None = None

    @property
    def canonical(self) -> str:
        return self.symbol.canonical

    @property
    def tradingsymbol(self) -> str:
        return self.symbol.tradingsymbol

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Instrument":
        token = payload.get("instrument_token")
        return cls(
            symbol=InstrumentSymbol(
                tradingsymbol=str(payload["symbol"]),
                exchange=str(payload.get("exchange", "NSE")),
            ),
            name=str(payload.get("name", "")),
            industry=str(payload.get("industry", "")),
            series=str(payload.get("series", "EQ")),
            isin=str(payload["isin"]) if payload.get("isin") else None,
            instrument_token=int(token) if token is not None else None,
        )


@dataclass(frozen=True)
class Nifty50Universe:
    index_name: str
    exchange: str
    retrieved_at: date
    source: str
    instruments: tuple[Instrument, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(item.tradingsymbol for item in self.instruments)

    @property
    def by_symbol(self) -> Mapping[str, Instrument]:
        return {item.tradingsymbol: item for item in self.instruments}

    @property
    def by_canonical(self) -> Mapping[str, Instrument]:
        return {item.canonical: item for item in self.instruments}

    def __len__(self) -> int:
        return len(self.instruments)

    def __iter__(self):
        return iter(self.instruments)

    def get(self, value: str) -> Instrument | None:
        raw = value.strip().upper()
        if ":" in raw:
            return self.by_canonical.get(raw)
        return self.by_symbol.get(raw)

    def require(self, value: str) -> Instrument:
        instrument = self.get(value)
        if instrument is None:
            raise KeyError(f"Not a NIFTY 50 constituent: {value}")
        return instrument

    def missing_from(self, available: Iterable[str]) -> list[str]:
        normalized = {item.strip().upper() for item in available}
        return [symbol for symbol in self.symbols if symbol not in normalized]

    def validate(self) -> list[str]:
        issues: list[str] = []
        if len(self.instruments) != 50:
            issues.append(f"Expected 50 constituents, found {len(self.instruments)}")
        symbols = [item.tradingsymbol for item in self.instruments]
        if len(symbols) != len(set(symbols)):
            issues.append("Duplicate tradingsymbols in universe")
        isins = [item.isin for item in self.instruments if item.isin]
        if len(isins) != len(set(isins)):
            issues.append("Duplicate ISINs in universe")
        for item in self.instruments:
            if item.symbol.exchange != self.exchange:
                issues.append(f"{item.canonical} is not on {self.exchange}")
            if item.series != "EQ":
                issues.append(f"{item.canonical} is not an EQ series instrument")
        return issues

    def require_valid(self) -> None:
        issues = self.validate()
        if issues:
            raise UniverseError("; ".join(issues))


def load_nifty50(path: str | None = None) -> Nifty50Universe:
    if path is None:
        resource = resources.files("ai_stock_analyzer.data").joinpath("nifty50.json")
        payload = json.loads(resource.read_text(encoding="utf-8"))
    else:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    exchange = str(payload.get("exchange", "NSE"))
    instruments = []
    for item in payload["constituents"]:
        enriched = dict(item)
        enriched.setdefault("exchange", exchange)
        try:
            instruments.append(Instrument.from_dict(enriched))
        except (SymbolError, KeyError, ValueError) as exc:
            raise UniverseError(f"Invalid constituent {item!r}: {exc}") from exc
    universe = Nifty50Universe(
        index_name=str(payload.get("index", "NIFTY 50")),
        exchange=exchange,
        retrieved_at=date.fromisoformat(payload["retrieved_at"]),
        source=str(payload.get("source", "")),
        instruments=tuple(instruments),
    )
    universe.require_valid()
    return universe
