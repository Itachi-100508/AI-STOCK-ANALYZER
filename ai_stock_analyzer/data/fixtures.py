from __future__ import annotations

import hashlib
import json
import random
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

from ai_stock_analyzer.market.bars import Bar
from ai_stock_analyzer.market.calendar import NSECalendar
from ai_stock_analyzer.market.constants import DAILY_INTERVAL
from ai_stock_analyzer.market.instruments import Nifty50Universe
from ai_stock_analyzer.market.symbols import canonical_symbol


def _seed_value(symbol: str, day: date, interval: str, seed: int) -> int:
    material = f"{seed}:{symbol}:{day.isoformat()}:{interval}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _base_price(symbol: str) -> float:
    digest = hashlib.sha256(symbol.encode("utf-8")).digest()
    return 50.0 + (int.from_bytes(digest[:2], "big") % 950)


def generate_bars(
    symbol: str,
    day: date,
    interval: str,
    calendar: NSECalendar | None = None,
    seed: int = 7,
    start_price: float | None = None,
) -> list[Bar]:
    calendar = calendar or NSECalendar()
    canonical = canonical_symbol(symbol)
    starts = calendar.session_bar_starts(day, interval)
    rng = random.Random(_seed_value(canonical, day, interval, seed))
    price = float(start_price) if start_price is not None else _base_price(canonical)
    sigma = 0.01 if interval == DAILY_INTERVAL else 0.0008
    bars: list[Bar] = []
    for start in starts:
        open_price = price
        close_price = max(1.0, open_price * (1.0 + rng.gauss(0.0, sigma)))
        high_price = max(open_price, close_price) * (
            1.0 + abs(rng.gauss(0.0, sigma / 2.0))
        )
        low_price = min(open_price, close_price) * (
            1.0 - abs(rng.gauss(0.0, sigma / 2.0))
        )
        low_price = max(0.01, low_price)
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)
        volume = int(rng.uniform(10_000, 500_000))
        bars.append(
            Bar(
                symbol=canonical,
                interval=interval,
                start=start,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=volume,
            )
        )
        price = close_price
    return bars


def generate_universe_bars(
    universe: Nifty50Universe,
    day: date,
    interval: str,
    calendar: NSECalendar | None = None,
    seed: int = 7,
) -> dict[str, list[Bar]]:
    return {
        instrument.canonical: generate_bars(
            instrument.canonical,
            day=day,
            interval=interval,
            calendar=calendar,
            seed=seed,
        )
        for instrument in universe
    }


def dump_bars(
    path: str | Path, bars_by_symbol: Mapping[str, Iterable[Bar]]
) -> None:
    payload = {
        canonical_symbol(symbol): [bar.to_dict() for bar in bars]
        for symbol, bars in bars_by_symbol.items()
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_bars(path: str | Path) -> dict[str, list[Bar]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        canonical_symbol(symbol): [Bar.from_dict(item) for item in items]
        for symbol, items in payload.items()
    }
