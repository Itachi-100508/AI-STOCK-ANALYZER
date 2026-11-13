# AI Stock Analyzer - Repository Audit

**Status:** inspection complete. No development has started. Awaiting explicit approval of the plan.

| Item | Value |
| --- | --- |
| Audit date | 2026-11-13 |
| Repository | https://github.com/Jakeschincariol/day-trader-skill |
| Commit inspected | `3d0f4ef6986f4984b7c6bd46f7ff4f87744c3abd` (2026-10-20, branch `main`) |
| Local clone | `third_party/day-trader-skill` (shallow clone, depth 1) |
| License | MIT, Copyright (c) 2026 Jake Schincariol |
| Method | Static reading of README, 11 `SKILL.md` files, 11 Python tools, JSON examples, tests and fixtures |
| Not done | No package install, no Python or shell script execution from the repo, no broker or exchange connection, no credentials, no order placement, no changes to the clone |

> **Safety declaration.** The original repository was not modified. Nothing in this audit places orders, connects to a broker, or uses real money. All statements below are based on reading the code and files. The repository's own test suite was **not executed** (that would violate the "do not execute repository scripts" rule); test quality is assessed by reading the tests. Where a claim depends on a runtime behaviour that only execution could confirm, it is marked as such.

---

## 0. Executive summary

1. **What this repository is.** It is not a standalone trading application. It is a pack of 11 Claude "skills" (instruction files plus standard-library Python command-line tools) that implement a US day-trading workflow. The LLM orchestrates the steps and talks to the user; Python does the arithmetic.
2. **Genuine quantitative logic exists, but it is modest.** The tools contain deterministic, testable implementations of Wilder RSI(14), SMA(20), a 20-day closing-high breakout, a simple bull-flag rule, a 20-day reclaim, opening-range breakout detection, ATR(14), stop/target arithmetic, position sizing, a pre-trade risk engine, and a seeded Monte Carlo simulator. There is no machine learning, no sentiment model, no confidence calibration, no portfolio optimiser and no self-learning loop.
3. **The "AI" is mostly orchestration and text interpretation.** The LLM chooses which tool to run, reads news and filings, writes summaries, asks the user for confirmation and explains results. It does not calculate prices or P&L; the Python tools do. This separation is good engineering and should be preserved.
4. **The system is tightly coupled to US markets.** It uses Nasdaq Trader symbol lists, NYSE hours and holidays for 2026-2027 only, New York time with US daylight saving, Yahoo Finance US endpoints, SEC EDGAR/XBRL, US House PTR disclosures, Alpaca/IBKR order shapes, USD and US ticker conventions.
5. **Strongest reusable assets:** the file-based pipeline contract, the closed-bar entry state machine, the opening-range logic, the risk-engine structure, the sizing arithmetic, the risk/approval fingerprint gate, the seeded Monte Carlo harness, the offline-fixture testing style, and the safety-first product posture.
6. **Weakest parts for India:** the data layer, the instrument master, the market calendar and session model, the broker/execution layer, the options model (absent), the cost model (absent), the news and fundamentals sources, and the backtesting/validation layer (the Time Machine is not a backtester).
7. **The Time Machine is a useful reality-check, not a predictor.** It bootstraps 60 sessions of 5-minute bars at the same time of day, conditions on the trade already triggering, ignores costs and slippage, and assumes independent bar draws. It is honest about being a simulation, but it must not be treated as validated edge.
8. **There is no options support.** `allow_options` is false, the risk engine blocks option contracts, and there is no chain, Greeks, implied volatility, lot-size, expiry or margin logic. NIFTY options are a separate build, not an adaptation.
9. **There is no self-learning.** No historical recommendation ledger, no outcome labels, no feature store, no model training, no walk-forward validation, no drift monitoring. The broker log is a starting point for a trade journal, not a learning dataset.
10. **Biggest risks:** data licensing and reliability in India, SEBI compliance for algo/advice products, execution safety, cost modelling, methodology overfitting, and the fact that the current "approval" gate is partly enforced by prompt instructions rather than by a hard execution service.

**Recommended first development task:** build an **India Market Core v0** (IST/NSE calendar, NIFTY 50 instrument master, canonical-to-provider symbol mapping, normalised bar schema, read-only data-provider interface, offline fixtures and tests) **plus a data-feasibility spike**. This is the foundation every later component depends on, and it can be built without credentials or real money.

---

## 1. Scope, method, and limits

### 1.1 What was inspected

- `README.md`, `LICENSE`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- All 11 `SKILL.md` instruction files
- All 11 Python tools: `scan.py`, `news.py`, `entry.py`, `exit.py`, `timemachine.py`, `check.py`, `size.py`, `ticket.py`, `alerts.py`, `facts.py`, `ptr.py`
- All example JSON files: config, alerts, targets, metrics, broker desktop config
- The 12 test modules plus `tests/_load.py`
- The offline fixtures, including a direct inspection of `TSLA-60d5m.json.gz` to check the Time Machine's session-count claim

### 1.2 What was not done

- No `pip install`, no virtual environment, no dependency installation
- No execution of any Python script, shell script or repository-provided command
- No calls to Yahoo, Nasdaq Trader, SEC, the House Clerk or Stooq
- No broker or exchange connection, no account access, no order creation
- No request for, storage of, or exposure of API keys, passwords or credentials
- No modification of the clone, no Git configuration changes, no history rewrite

### 1.3 Limits of a static audit

- The test suite was not run, so "tests exist" does not mean "tests pass".
- Live endpoint behaviour (Yahoo reliability, NSE data availability, broker APIs) cannot be confirmed from the code alone.
- Some findings are potential issues that depend on runtime conditions; they are labelled as such.
- Indian-market regulatory and market-structure statements below are written as engineering requirements to be verified against current official sources (NSE, BSE, SEBI, RBI, brokers), not as legal advice.

---

## 2. Repository structure overview (A)

### 2.1 Top-level tree

```
day-trader-skill/
  .claude-plugin/
    marketplace.json          # Claude plugin marketplace metadata
    plugin.json               # plugin manifest, version 2.0.0
  trader-scanner/             # SKILL.md + scan.py
  trader-news/                # SKILL.md + news.py
  trader-entry/               # SKILL.md + entry.py
  trader-exit/                # SKILL.md + exit.py
  trader-timemachine/         # SKILL.md + timemachine.py
  trader-risk/                # SKILL.md + check.py
  trader-budget/              # SKILL.md + size.py, config.example.json, targets.example.json
  trader-broker/              # SKILL.md + ticket.py, claude_desktop_config.example.json
  trader-alerts/              # SKILL.md + alerts.py, alerts.example.json
  trader-analyst/             # SKILL.md + facts.py, metrics.example.json
  trader-pelosi/              # SKILL.md + ptr.py
  tests/                      # 12 unittest modules + _load.py + offline fixtures
  README.md
  LICENSE
```

### 2.2 Size and test inventory (measured statically)

| Measure | Value |
| --- | --- |
| Skill folders | 11 |
| Python tools | 11 |
| Tool Python lines (excluding tests) | 7,528 |
| Test modules | 12 (plus `_load.py`) |
| Test Python lines | 3,904 |
| Test methods (counted by `def test_`) | approximately 315 |
| Total repository size | 1.07 MB |
| Third-party Python dependencies | none; standard library only |
| Declared minimum Python | 3.8 (asserted by `tests/test_repo.py`) |

The test suite is unusually large relative to the tools and is built around offline fixtures cut from real data. `tests/test_repo.py` also enforces repository-level invariants (11 skill folders, frontmatter, safety language, Python 3.8 compatibility, paper-trading defaults). This is a strong engineering signal.

### 2.3 Packaging model

Each skill is a folder with:

- `SKILL.md`: YAML frontmatter (`name`, `description`, `argument-hint`) plus instructions for the LLM
- One Python CLI tool (except that the tool is optional in principle; the README says a `SKILL.md` alone can run as a prompt-only mode)

The plugin manifests point Claude Code at the repository root. `${CLAUDE_SKILL_DIR}` is used in the instructions so the LLM can locate the tool. The tools are ordinary CLI programs with `argparse`, JSON input/output and exit codes.

**Implication for us:** the Claude plugin packaging is not reusable as our application architecture. The Python modules are reusable; the orchestration and skill packaging must be replaced or wrapped by our own service/UI.

### 2.4 The file contract (`trader/` folder)

The system is a file-based pipeline. Every skill reads what an earlier skill wrote, and writes JSON for the next one.

| File | Written by | Read by | Purpose |
| --- | --- | --- | --- |
| `trader/universe.txt` | scanner (`universe`) | scanner (`daily`, `orb`) | One `SYMBOL|Name` per line |
| `trader/watchlist.json` | scanner (`daily`, `orb`) | news, entry | Scan hits and counts |
| `trader/config.json` | user (from example) | scanner, entry, exit, risk, budget, alerts | Budget, limits, windows, flags |
| `trader/entry.json` | entry | exit | Triggered setup, time, price, opening range |
| `trader/plan.json` | exit | timemachine, budget, alerts | Entry, stop, target, R, flat-by |
| `trader/timemachine.json` | timemachine | user / later review | Monte Carlo odds, history, verdict |
| `trader/orders.json` | budget, broker (`flatten`) | risk, broker | Proposed order(s) |
| `trader/state/risk.json` | risk | broker | PASS/BLOCK verdicts with fingerprints |
| `trader/state/broker.json` | broker | risk, broker | Approval, placement, fill log; max loss per entry |
| `trader/portfolio.json` | broker | budget, risk, alerts, news | Cash and holdings |
| `trader/prices.json` | alerts | budget, risk | Latest quotes with timestamps |
| `trader/alerts.json` | user / alerts | alerts | Alert rules |
| `trader/state/alerts.json` | alerts | alerts | Which rules rang, once |
| `trader/state/news.json` | news | news | Seen items and CIK cache |
| `trader/metrics.json` | analyst (`--metrics`) | user | Fundamentals export |
| `trader/state/pelosi.json` | pelosi | pelosi | Seen PTR DocIDs |

This contract is simple, inspectable and easy to test. It is also single-user, single-machine, with no schema versioning, no locking and no transaction boundaries. Some writes use `os.replace` for atomicity, but cross-file consistency is not guaranteed.

### 2.5 Data sources used

| Source | Used by | Notes |
| --- | --- | --- |
| Yahoo Finance chart v8 (`query2`, fallback `query1`) | scanner, entry, exit, timemachine, alerts, news | Free, unofficial, delayed, can rate-limit |
| Yahoo Finance spark v7 | scanner | Batch closes, 20 symbols per request |
| Yahoo Finance headline RSS | news | Per-ticker headlines |
| Nasdaq Trader symbol directories | scanner | `nasdaqlisted.txt`, `otherlisted.txt` |
| SEC EDGAR company facts, submissions, archives | analyst | XBRL, 10-Q/10-K/8-K |
| SEC EDGAR company Atom feed | news | 8-K filings |
| SEC `company_tickers.json` | news, analyst | Ticker to CIK |
| Stooq CSV | alerts | Parser kept; documented as returning 404 at inspection time |
| US House Clerk disclosure ZIP/PDFs | pelosi | PTR filings; `pdftotext` optional |

No paid vendor, no exchange feed, no broker data API, no news API, no database.

### 2.6 Time and calendar assumptions

- Session: 09:30 to 16:00 New York time, with 13:00 early closes on a short list of dates.
- Time zone: America/New_York, with US daylight-saving rules implemented by hand.
- Holidays: hardcoded for 2026 and 2027 only. For any other year the tools warn that the calendar is unknown.
- Bars: 5-minute grid for scanning, entry and Time Machine; 1-minute optional for entry; daily closes for the pre-market scan.
- The full calendar and time-zone helpers are duplicated in six tools (`scan.py`, `entry.py`, `exit.py`, `timemachine.py`, `check.py`, `alerts.py`); the time-zone offset helper is duplicated in nine tools. This is a code-drift risk.

---

## 3. Explanation of how the existing system works (B)

### 3.1 Runtime and orchestration model

The user interacts with Claude. Claude reads a `SKILL.md`, runs a Python CLI with `python3`, reads stdout/JSON, and talks back. The Python process is stateless between calls; all state lives in `trader/`. A background `watch` loop can poll a bar-by-bar setup, and a `/loop` or scheduled task can re-run news or alerts.

There is no server, no queue, no database, no scheduler of its own, no authentication and no multi-user support. The "system" is a convention for files plus an LLM that follows instructions.

### 3.2 The trade lifecycle

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker
                                                                     |
alerts: stop, target, flat-by, opening bell                          v
                                                               broker/MCP
news / analyst / pelosi: on a schedule or on demand
```

1. **Scanner** builds a universe, runs a daily pre-market scan or an intraday opening-range scan, and writes `watchlist.json`.
2. **News** reads the watchlist, plan and portfolio, fetches headlines and filings, deduplicates, tags and reports moves.
3. **Entry** watches a chosen symbol bar by bar and writes `entry.json` when a completed bar closes above the level.
4. **Exit** computes a stop and target before the trade, writes `plan.json`.
5. **Time Machine** replays the rest of the day 10,000 times and re-runs the rule on past sessions.
6. **Budget** sizes the position to the tightest of several limits and writes one bracket order.
7. **Risk** checks the exact order against limits, writes PASS/BLOCK with a fingerprint.
8. **Broker** renders a ticket, records an explicit yes, and only then the LLM calls a broker MCP tool. The user must also click "Allow once" in Claude's permission card.
9. **Alerts** watches the stop, target and flat-by time while the trade is open.

### 3.3 Safety and approval model

This is the strongest part of the product design:

- **Paper by default:** `"paper": true` in the example config, and the broker instructions default to Alpaca paper.
- **Three gates for an order:** (1) `trader-risk` PASS for the exact order today, matched by a SHA-256 fingerprint of the core order fields; (2) the user types an explicit yes for that one order; (3) the user clicks "Allow once" on Claude's own tool-permission card.
- **No autonomous ordering:** `trader-broker` never places orders from a background task; `ticket.py` itself never talks to a broker.
- **Exit protection:** a sell that only reduces an existing position is never blocked by day limits, entry windows, loss limits or reward:risk.
- **Clear refusals:** invalid stops, targets, sizes, days, blocked tickers and reward:risk failures produce plain-language refusals.
- **Honest language:** the docs repeatedly say "not financial advice", "most people who day trade lose money", "a stop is a plan, not a guarantee", "the Time Machine is a simulation, not a prediction".

**Gap for our architecture:** the Python tool does not enforce the broker call. The actual hard barrier is the MCP tool permission. If an LLM ignores its instructions, or if a malicious news item prompt-injects it, the only remaining barrier is the permission card. For our independent system, approval and order placement must be enforced in a separate execution service, not in a prompt.

### 3.4 State and reproducibility

- File-based JSON state is easy to inspect and test.
- Some writes use a temporary file plus `os.replace`, which is good.
- There is no locking. Concurrent `watch`, `check`, `news` and `alerts` runs can race or overwrite state.
- The Time Machine uses `random.Random(seed)` with seed 19 by default, so a run is repeatable on the same data.
- There is no snapshot/versioning of input data, so a later run can differ when Yahoo revises or backfills bars.

### 3.5 Genuine quantitative logic versus AI instructions

**Deterministic quantitative logic in Python:**

- Wilder RSI(14) on daily closes (`scan.py:485-495`)
- SMA(20), 20-day closing-high breakout, bull-flag heuristic, MA reclaim, oversold and oversold-bounce rules (`scan.py:516-539`)
- Opening-range construction and breakout confirmation (`scan.py:584-644`, `entry.py:408-552`)
- ATR(14) (`exit.py:469-484`)
- Stop/target computation with exact-cent rounding (`exit.py:270-333`)
- Position sizing and limit comparison (`size.py:305-415`)
- Pre-trade risk checks (`check.py:373-702`)
- Seeded Monte Carlo bootstrap and historical replay (`timemachine.py:335-490`)
- Calendar, session, daylight-saving and quote-freshness logic
- Alert evaluation and deduplication (`alerts.py:428-494`)

**What the LLM does:**

- Chooses which skill to run and in what order
- Interprets news headlines, SEC filings and PTR PDFs
- Writes briefs, summaries and explanations
- Decides whether a headline changes the trade thesis
- Asks the user for confirmation and records the reply
- Explains PASS/BLOCK and Monte Carlo results

**What is absent:**

- No trained ML model, no classifier, no regressor, no neural network
- No sentiment scoring model (only keyword tags)
- No confidence calibration
- No expected-value or probability calibration beyond the Monte Carlo frequencies
- No feature store, model registry or learning loop
- No portfolio optimisation, correlation analysis or factor model

**Conclusion:** the repository has a **real but modest hand-built quant core**; it is not "AI trading" in the machine-learning sense. The LLM is an orchestration and language layer. This is actually a healthy separation for our project, but it means the "self-learning AI" must be built from scratch.

### 3.6 Component-by-component assessment

Each component is assessed on: what it does, how it works, what is reusable, what is US-specific, what India needs, and bugs/limitations.

#### 3.6.1 trader-scanner (`scan.py`, 1,083 lines)

- **What it does:** Builds a US stock universe, runs a pre-market daily-close scan (20-day breakout, bull flag, MA20 reclaim, oversold, oversold bounce) and an intraday opening-range breakout scan, then writes `watchlist.json`.
- **How it works:** Downloads Nasdaq Trader symbol directories and filters test issues, ETFs, units, warrants, rights, notes, preferreds and similar. Daily scan uses Yahoo spark (20 symbols per request, 3 months of daily closes); computes Wilder RSI(14), SMA(20), 20-day closing high, 10-session run and 5-session range. ORB uses stage 1 spark closes to identify candidates whose post-range close is at or above the highest range close, then stage 2 v8 charts with real highs and lows; requires a contiguous 5-minute grid; a hit is the first completed bar that closes above the range high. Results are sorted by price times volume.
- **Reusable:** the ORB logic, two-stage filtering, contiguous-bar usability check, RSI and SMA functions, rule-table structure, polite batching and fallback hosts, offline file loading, JSON contract, CLI design and pure functions that are easy to unit test.
- **US-specific:** Nasdaq Trader universe rules, ETF/test-issue filters, NYSE calendar and 09:30-16:00 ET session, ET daylight saving, Yahoo spark coverage, USD price floor and US volume floor, US ticker suffixes.
- **India build:** NIFTY 50 universe (later NIFTY 100/500), NSE symbol master and series filter (`EQ`), ISIN and instrument master, IST session (09:15-15:30, pre-open 09:00-09:15), NSE/BSE holiday calendar, rupee price and liquidity floors calibrated to Indian volumes, circuit/price-band handling, F&O ban list, index reconstitution handling, corporate-action-adjusted prices, and a provider adapter that does not rely on Yahoo.
- **Bugs/limitations:** uses unofficial Yahoo data; daily setups use closes only and a 20-day *closing* high, not an intraday high; no split/bonus/dividend adjustment; `to_yahoo()` replaces `.` with `-` (`scan.py:270-271`), which breaks Yahoo NSE suffixes such as `.NS`; no URL encoding for symbols containing `&`; stage 2 can stop at 200 candidates and label the result PARTIAL; no relative strength versus NIFTY, no sector neutralisation, no VWAP/MACD/Bollinger/candlestick patterns; no cost or slippage model; hardcoded calendar years 2026-2027; no test of live endpoints.

#### 3.6.2 trader-news (`news.py`, 546 lines)

- **What it does:** Fetches Yahoo Finance headlines and SEC 8-K filings for the watchlist, plan and portfolio, flags stocks moving at least 3% from the previous close, tags items (earnings, analyst, deal, halt, regulatory, macro and others), removes already-seen items, and writes a daily state file.
- **How it works:** RSS and Atom parsing with `xml.etree.ElementTree`; RFC 822 and ISO 8601 time parsing; ticker-to-CIK mapping from SEC; keyword tagging; SHA-based fingerprint deduplication kept for 30 days; `--json` output; `--dry-run` and `--all` modes.
- **Reusable:** feed-adapter pattern, dedupe/fingerprint logic, state retention, tagging structure, move detection, "what is new since last check" semantics, and the instruction to treat headlines as leads rather than facts.
- **US-specific:** Yahoo US RSS, SEC EDGAR and 8-K form types, CIK identifiers, US tickers and US region settings.
- **India build:** NSE and BSE corporate announcements, SEBI filings, RBI and government releases, exchange results calendar, board-meeting and dividend announcements, insider/SAST disclosures, shareholding patterns, credit-rating actions, promoter pledges, index changes, and licensed news feeds. Entity resolution is harder: company names, group companies, subsidiaries and ticker changes. Multilingual content (English/Hindi/regional) may matter. Prompt-injection defence is essential because headlines are untrusted text.
- **Bugs/limitations:** keyword tagging is crude and is not sentiment analysis; no entity linking across tickers; no source-reliability score; no importance ranking; no earnings-date feed (the analyst docs admit this); no 10-Q or transcript ingestion; no India coverage; no notification delivery (the LLM is expected to poll); XML parsing of untrusted feeds should use a hardened parser such as `defusedxml`; no schema validation of feeds.

#### 3.6.3 trader-entry (`entry.py`, 960 lines)

- **What it does:** Watches one symbol or a watchlist, bar by bar, and reports `waiting`, `triggered`, `expired` or `no-data`. Supports opening-range breakout or a user-supplied level, 5-minute or 1-minute bars, an optional volume multiple, entry-window limits and a replay clock.
- **How it works:** Fetches Yahoo 1-day chart data; drops off-grid live ticks and incomplete bars; builds the opening range from the first N bars; triggers on the first completed bar whose close is strictly above the level, within the configured window; handles holidays, early closes, pre-open and after-close phases; `check --write` or `watch` writes `entry.json`.
- **Reusable:** the closed-bar state machine, `evaluate()` as a pure function, the simulated clock and `--offline` replay, `watch` loop with error tolerance, configurable windows, and the JSON contract.
- **US-specific:** NYSE 09:30-16:00 ET session, ET DST, NYSE holidays and 13:00 early closes, Yahoo 1m/5m data, US ticker mapping, long-only assumption.
- **India build:** 09:15 open, 09:00-09:15 pre-open auction, IST with a fixed +05:30 offset, NSE/BSE calendar, opening range definition for Indian equities, broker/vendor intraday data, circuit and halt detection, volume-filter calibration, MIS square-off constraints, NIFTY spot versus futures versus options underlying, expiry-day behaviour, and a data-latency model.
- **Bugs/limitations:** the opening range can be computed from fewer than all range bars if a bar is missing (`entry.py:482-499`), whereas the scanner rejects such charts as unusable (`scan.py:610-619`); this inconsistency should be resolved deliberately. No circuit/halt/price-band detection. One trigger per setup per day. Long-only. No re-entry or invalidation logic. No costs or slippage. Depends on Yahoo bar timestamps and a 60-second settle grace; a stale feed can still produce a late or imperfect close. The "market closed" path depends on the hardcoded calendar.

#### 3.6.4 trader-exit (`exit.py`, 735 lines)

- **What it does:** Sets the stop and target before entry. Stop rules are opening-range midpoint, opening-range low, a user price, a percentage, or K times ATR(14). Targets are 1R, 2R, 1.5R, or a user price. Refuses invalid or too-tight stops and writes `plan.json`.
- **How it works:** Decimal arithmetic in cents; the stop rounds away from the entry; risk is entry minus stop; target is entry plus R times risk; ATR is computed on the session's bars up to the entry bar; flat-by defaults to 15:55 ET and shifts on early-close days.
- **Reusable:** exact-cent arithmetic, stop/target validation, ATR calculation, opening-range stop rules, `plan.json` contract, refusal messages, flat-by concept.
- **US-specific:** US cent rounding, NYSE flat-by and early close, long-only, USD.
- **India build:** rupee tick sizes (not always 0.01), broker MIS square-off times, F&O lot rounding, options premium and Greeks, expiry-day risk, price bands, costs, and separate stop semantics for equity versus options. A fixed "flat by 15:55" is too late for many Indian intraday brokers, which square off earlier.
- **Bugs/limitations:** assumes two-decimal cents; ATR is based only on the current session's bars, which can be very few early in the day; opening-range midpoint may be too tight or too wide for volatile Indian names; no volatility-regime adjustment; no trailing stop; no scaling out; no gap-risk modelling; no costs; no event-risk blackout; long-only.

#### 3.6.5 trader-timemachine (`timemachine.py`, 956 lines)

- **What it does:** Takes a plan (entry, stop, target, entry bar), fetches 60 days of 5-minute bars, replays the rest of the session 10,000 times, re-runs the same rule on every past full session, and prints odds of target first, stop first, neither, green, average R, price percentiles, a fan chart and a one-line verdict.
- **How it works:** Keeps full 78-bar sessions before the plan date; converts each bar to open/high/low/close ratios to the previous close; for each replay, samples a past bar from the same time of day plus or minus 2 slots, scales it to the current price, and checks stop first then target. A gap through the stop counts as -1R. History replay computes the opening range and entry on each past session and applies the same stop/target rule. The verdict compares the target's share of one-sided outcomes to the break-even share `1/(1+R)`.
- **Reusable:** the simulation harness, seeded reproducibility, ratio-based sampling, conservative same-bar assumption, historical rule replay, percentile/histogram reporting, verdict logic, and the honesty about simulation limits.
- **US-specific:** 78-bar 09:30-16:00 ET session, 60-day Yahoo 5-minute history, ET calendar, US ticker mapping.
- **India build:** 75-bar 09:15-15:30 IST session, IST time zone, longer and cleaner historical data from a licensed source, corporate-action adjustment, NSE circuit/halt handling, event calendars (RBI policy, budget, expiry), futures versus spot, options expiry and Greeks, and a cost/slippage model. For options, a completely different simulator is needed.
- **Bugs/limitations:** The Monte Carlo assumes independent draws from the pool. It preserves time-of-day but destroys serial correlation, volatility clustering and regime persistence. It conditions on the entry already triggering, so it estimates P(target or stop | entry), not P(trade). It ignores costs, slippage, taxes, liquidity and market impact. The pool is only about 59 prior sessions, so the sample is small and regime-sensitive. The history replay supports the opening-range rule only; for other setups it is skipped (`timemachine.py:730-736`). The history replay does not apply the live volume filter or entry-window rules (`timemachine.py:451-490`). A bar that touches both stop and target counts as a stop, which is conservative but arbitrary. The same default seed 19 is reused, which is good for reproducibility but can create a false sense of stability. It is not a backtester and does not validate a strategy across the universe or across regimes.

**Verification note:** the fixture `tests/fixtures/trader-timemachine/TSLA-60d5m.json.gz` contains 4,619 timestamps across 60 distinct UTC dates (2026-07-27 to 2026-10-19), which is consistent with the documented 59 prior sessions plus the entry day. The "60 days / 59 sessions" claim is therefore internally consistent with the fixture.

#### 3.6.6 trader-risk (`check.py`, 819 lines)

- **What it does:** The pre-trade gate. Prints PASS or BLOCK per order with reasons. Checks format, asset type, short sales, blocked tickers, order size, position cap, cash buffer and margin, stop presence and side, max loss per trade, reward:risk, daily loss, trades per day, entry window, PDT (optional), duplicates and daily order limit. Exits are never blocked by day limits.
- **How it works:** A pure `check()` function takes orders, config, portfolio, prices and broker state. It simulates the batch in file order as if each passed order filled, so combined breaches are caught. The reference entry price is the limit price, or the higher of the plan entry and a fresh quote under 15 minutes old. It writes `state/risk.json` with a fingerprint per order.
- **Reusable:** the entire risk-engine structure, entry-versus-exit distinction, batch simulation, fingerprinting, config schema, warning system, plain-language reasons and testability.
- **US-specific:** US ticker regex and OCC option-symbol regex, Alpaca field names, PDT rule, NYSE calendar and windows, USD, T+0-style intraday round trips, US cash/margin model.
- **India build:** SEBI/broker margin (SPAN plus exposure), MIS product rules, T+1 settlement and the inability to sell same-day delivery shares, restrictions on retail short selling, F&O lot sizes, ban lists, price bands and circuit halts, broker square-off times, Indian order types (SL-M, SL-L, cover, bracket where offered), unique algo IDs, exchange and regulatory charges, NSE symbol validation, and separate option Greeks/expiry/margin risk.
- **Bugs/limitations:** `TICKER = ^[A-Z]{1,5}([.\-][A-Z]{1,2})?$` (`check.py:87`) rejects most NSE symbols because many are longer than five characters, and rejects names with `&`. `OCC` (`check.py:86`) is the US option-symbol format, not NSE. PDT is irrelevant in India and must be replaced. Daily loss counts the full max loss of every entry, not realised losses, which is conservative but can understate available risk after winners. No portfolio-level correlation, sector concentration, liquidity/ADV cap, event-risk blackout, options Greeks or margin model. It depends on the freshness and accuracy of local `portfolio.json` and `prices.json`; there is no broker reconciliation. The fingerprint covers only the core Alpaca fields, so a changed `why`/`plan` note does not invalidate a PASS (probably intentional).

#### 3.6.7 trader-budget (`size.py`, 881 lines)

- **What it does:** Converts a plan into a position size and one proposed bracket order. Whole shares only. The size is the smallest of four limits: max loss per trade, position cap, max order size and cash after the buffer. It states which limit decided the size, refuses zero-size or invalid plans, and writes `orders.json`. A weights mode allocates a budget across a list by weight.
- **How it works:** Integer-cent arithmetic; `shares_for()` floors the dollar limit divided by the per-share price; the reference price is the plan entry or a fresher higher price, never a lower price; reward:risk and minimum order checks produce refusals; the bracket order uses Alpaca `place_stock_order` fields plus `why` and `plan` notes that are not sent to the broker.
- **Reusable:** sizing arithmetic, limit transparency, refusal semantics, config schema, weights allocator, bracket-order abstraction (to be adapted), and the "stop decides the size" principle.
- **US-specific:** Alpaca bracket-order schema, USD, whole shares, cash equity, no lot sizes, no margin products.
- **India build:** lot-based sizing for F&O, margin-based sizing, product codes (MIS/CNC/NRML), tick size, brokerage and statutory costs, exposure caps, SEBI margin, options premium budgeting and max-loss semantics, and broker-specific order types. Bracket orders are not universally available for Indian equity; many brokers offer only internal SL/cover products.
- **Bugs/limitations:** whole-share bracket constraint is Alpaca-specific; no gap risk beyond the stop; no costs; no correlation or portfolio heat beyond the daily loss cap; weights mode produces plain buys with no stops and is blocked by `require_stop` unless a separate config is used; no options; no fractional equity; the "higher price only" rule is conservative for risk but can still oversize if the entry is stale and the price later falls (the stop risk is then smaller, so this is acceptable).
- **Note:** the sizing is mathematically sound and well tested by design, but it is a single-trade sizer, not a portfolio allocator.

#### 3.6.8 trader-broker (`ticket.py`, 720 lines)

- **What it does:** Renders plain-language order tickets, checks that a user reply is an explicit yes for that exact order, matches the order to a same-day risk PASS by fingerprint, records approvals/results/fills, updates the portfolio, and builds a flatten ticket. It documents Alpaca's official MCP server and the IBKR connector.
- **How it works:** The Python tool never contacts a broker. It reads `orders.json`, `state/risk.json`, `state/broker.json`, `portfolio.json` and `plan.json`. The LLM shows the ticket, records the user's yes with `ticket.py approve`, then calls the MCP broker tool with exactly the printed JSON. A second approval card is enforced by Claude's tool permissions. Fills are recorded manually or from broker responses.
- **Reusable:** the three-gate pattern, ticket rendering, yes parsing, fingerprint matching, broker log, portfolio update, flatten flow, paper-first posture and setup documentation.
- **US-specific:** Alpaca MCP, IBKR connector, US order fields, bracket semantics, USD, US market hours and PDT.
- **India build:** a broker adapter for Kite Connect, Upstox, Angel One SmartAPI, Dhan, Fyers, Groww or another provider; OAuth/token lifecycle; static IP and exchange API requirements; product and order-type mapping; lot sizes; order-state webhooks; reconciliation; idempotency; rate limits; audit logs; SEBI algo registration and broker approval; and a hard approval service outside the LLM.
- **Bugs/limitations:** the yes parser is heuristic (it rejects questions, batch words and doubt words, and checks symbols and numbers) but it is not a cryptographic approval. There is no idempotency key, no order state machine, no partial-fill handling beyond manual recording, no cancellation flow beyond documentation, no broker reconciliation, and no encryption/immutable audit log. File-based state can race. The actual order placement depends on the LLM following instructions and on MCP permissions; the Python tool cannot stop a rogue tool call by itself.

#### 3.6.9 trader-alerts (`alerts.py`, 787 lines)

- **What it does:** Manages price, stop, target, percent-move, time-of-day and opening-bell alerts. Knows the NYSE clock and holidays, fetches delayed quotes from Yahoo or Stooq, rings each rule once, and writes `prices.json` for sizing and risk.
- **How it works:** Rules live in `alerts.json`; state in `state/alerts.json`. Evaluation compares quotes to thresholds or the clock; `--from-plan` creates stop, target and flat-by rules for the plan's date; early-close time rules shift three hours earlier; `quote --write` updates `prices.json` with timestamps.
- **Reusable:** alert model, dedupe and rearm logic, quote-adapter interface, clock utilities, `prices.json` contract, plan-to-alert generation.
- **US-specific:** NYSE hours and holidays, ET with US DST, Stooq `.us` symbols, Yahoo US tickers, 13:00 early closes.
- **India build:** IST, NSE/BSE calendar, pre-open and closing sessions, no DST, broker or vendor quote feed, circuit/halt awareness, quote freshness, NSE symbols, special sessions, and real notification delivery (push, email, Telegram, webhook). The current tool only prints to stdout and relies on the LLM or a loop to notice.
- **Bugs/limitations:** polling, not streaming, so it can miss a spike between checks; free quotes are delayed; the time-zone and holiday logic is US-specific and ends in 2027; there is no delivery channel; no volume or Greeks alerts; no quote entitlement; state races are possible; the one-retry backoff is minimal.

#### 3.6.10 trader-analyst (`facts.py`, 640 lines)

- **What it does:** Reads SEC XBRL company facts, the latest 10-Q/10-K and the latest earnings 8-K, then reports revenue, margins, net income, diluted EPS, quarter-by-quarter changes, year-on-year changes and trailing-twelve-month figures. It can export `metrics.json`.
- **How it works:** Maps US GAAP concepts, derives Q4 as the 10-K year minus the three reported quarters, matches year-ago periods with a tolerance, detects stale facts versus the newest filing, flags when net income exceeds operating income, and finds the EX-99.1 press release.
- **Reusable:** concept-mapping approach, quarterly derivation, year-on-year matching, staleness detection, metrics export, and the discipline of using filed numbers over press releases.
- **US-specific:** SEC EDGAR, CIK, US GAAP tags, 10-Q/10-K/8-K, US fiscal calendars, USD.
- **India build:** NSE/BSE XBRL financial results, Ind AS concept mapping, consolidated versus standalone statements, Indian fiscal year (April-March), quarterly and annual results, investor presentations, earnings calls, shareholding patterns, segment data, and INR. The SEC concepts do not map one-to-one to Indian filings.
- **Bugs/limitations:** no estimates or guidance; no transcript fetching (the LLM must read a pasted transcript); no earnings-date source; derived Q4 EPS is approximate; banks and insurers have no gross margin; facts can lag filings; no valuation or peer comparison; no India coverage.

#### 3.6.11 trader-pelosi (`ptr.py`, 640 lines)

- **What it does:** Watches US House Periodic Transaction Reports, reads the yearly index ZIP, filters by member and filing type, downloads PTR PDFs, converts them to text with `pdftotext` if available, parses rows (owner, asset, ticker, buy/sell, options strike/expiry, trade date, amount range, disclosure delay), remembers seen DocIDs, and flags trades in the user's holdings. Senate reports are a documented manual route.
- **How it works:** Downloads and parses XML from the House Clerk, regex-parses `pdftotext -layout` output, stores state in `state/pelosi.json`, optionally reads PDFs, and renders rows with links.
- **Reusable:** disclosure-ingestion pattern, incremental "new since last check" state, document parsing, caveats about public and late information, and the ethics of not implying inside information.
- **US-specific:** US House Clerk, STOCK Act PTRs, US politicians and US tickers. There is no direct Indian equivalent.
- **India build:** this skill is **not applicable as-is**. Possible analogues are SEBI insider-trading disclosures, SAST/regulatory filings, promoter shareholding and pledge changes, bulk/block deals, mutual-fund and FII/DII flow data, and exchange announcements. The ingestion pattern can be reused; the domain logic must be replaced. Ethically, avoid implying that following politicians or insiders is a proven edge.
- **Bugs/limitations:** PDF parsing is brittle; `pdftotext` is an optional external binary; option description parsing covers a limited set of formats; filings are late by design; no return claims; no India relevance.

---

## 4. Reusable components (C)

### 4.1 Reuse directly (with attribution and tests)

| Asset | Location | Why it is useful |
| --- | --- | --- |
| Opening-range construction and breakout confirmation | `trader-scanner/scan.py:584-644`, `trader-entry/entry.py:408-552` | Clear, testable rule with closed-bar discipline |
| Wilder RSI(14), SMA(20), ATR(14) | `scan.py:485-495`, `exit.py:469-484` | Small, dependency-free reference implementations |
| Exact-cent stop/target arithmetic and validation | `exit.py:270-333` | Good rounding and refusal patterns |
| Position-sizing limit comparison | `size.py:305-415` | Transparent "which limit binds" logic |
| Risk-engine structure and entry/exit distinction | `check.py:373-702` | Strong skeleton for an India rules engine |
| Fingerprint-and-approval gate | `check.py:271`, `ticket.py:145-149`, `ticket.py:271-340` | Useful pattern for order integrity |
| Seeded Monte Carlo harness | `timemachine.py:335-424` | Reusable simulation scaffold, with caveats |
| Historical rule replay | `timemachine.py:451-490` | Useful pattern for event-driven backtests |
| Offline-fixture test style | `tests/` | Excellent model for deterministic tests |
| File-based pipeline contract | `trader/*.json` | Simple and inspectable, good for a prototype |
| Safety language and paper-first posture | all `SKILL.md` files | Aligns with our no-guarantee requirement |

### 4.2 Reuse with adaptation

| Asset | Adaptation needed |
| --- | --- |
| Calendar and time-zone helpers | Replace US/NYSE/ET with IST/NSE/BSE; extract one shared module instead of six copies |
| Yahoo data adapters | Replace with a provider interface and a licensed/broker feed; keep an offline adapter for tests |
| Ticker normalisation | Replace `.` to `-` with an explicit canonical-to-provider mapping (for example `RELIANCE` to `RELIANCE.NS`) |
| Universe builder | Replace Nasdaq Trader rules with NSE instrument master and NIFTY 50 constituents |
| Broker ticket and state | Replace Alpaca fields with a broker-neutral order model and an Indian broker adapter |
| Risk rules | Replace PDT, US windows, US ticker and OCC regex, and USD assumptions with Indian rules |
| Sizing | Add lot sizes, margin, product codes and costs |
| News and analyst adapters | Replace SEC/Yahoo sources with NSE/BSE/SEBI and licensed news/fundamental data |
| Alert delivery | Add a real notification channel and streaming or frequent polling |
| Time Machine | Re-parameterise the session, add costs, and treat it as a diagnostic, not a validator |

### 4.3 Rewrite or build new

- Data ingestion, normalisation, storage and quality control
- Instrument master and corporate-action handling
- Multi-timeframe feature engine (VWAP, MACD, EMA/SMA, Bollinger, ADX, volume profile, support/resistance, candlestick patterns)
- Recommendation layer with confidence, expected value, holding duration, invalidation and "no trade" decisions
- Event-driven backtester with costs, slippage, latency, walk-forward and multiple-testing control
- Trade journal, recommendation ledger and outcome labelling
- Self-learning pipeline (feature store, model registry, shadow mode, drift monitoring)
- Portfolio and options risk (Greeks, margin, expiry, lot sizing)
- Execution service with idempotency, reconciliation, kill switch and hard approval
- Observability, authentication, secrets management, audit logging and CI/CD

### 4.4 License and attribution

The repository is MIT licensed. Reuse is permitted with the copyright and permission notice. If we copy code, we should:

- Keep the MIT notice and attribute Jake Schincariol and the repository.
- Record the exact commit used.
- Avoid copying the repository's test invariants that are specific to its README (they are irrelevant to us).
- Prefer a clean-room implementation for anything we intend to change heavily, with attribution for the original idea.

---

## 5. Components requiring Indian-market replacements (D)

### 5.1 Market structure differences that drive the design

| Area | Current US assumption | India reality to design for |
| --- | --- | --- |
| Session | 09:30-16:00 ET | 09:15-15:30 IST; pre-open 09:00-09:15; special sessions and muhurat trading |
| Time zone | America/New_York with US DST | Asia/Kolkata, UTC+05:30, no DST |
| Calendar | NYSE holidays hardcoded for 2026-2027 | NSE/BSE annual holiday list; settlement and expiry calendars; special sessions |
| Settlement | Intraday round trips; T+0 style for day trades | T+1 equity settlement; same-day sale of delivery shares is restricted; intraday is a broker product (MIS) |
| Short selling | Configurable, US model | Retail cash-market shorting is restricted; intraday shorting depends on product and broker; F&O is separate |
| Order types | Alpaca bracket orders | Broker-specific SL-M, SL-L, cover, bracket and product codes; no universal bracket order |
| Costs | Ignored | STT, exchange transaction charges, SEBI turnover fees, stamp duty, GST, brokerage, DP charges, and slippage |
| Price limits | No general price bands | Exchange price bands, dynamic bands, circuit halts, F&O ban periods |
| Instruments | US stocks and ETFs | NIFTY 50 equities, NIFTY index, futures, options with lot sizes, expiries and margins |
| Data | Yahoo, SEC, Nasdaq Trader | NSE/BSE, broker APIs, licensed vendors; redistribution restrictions |
| Fundamentals | SEC XBRL and US GAAP | NSE/BSE XBRL, Ind AS, consolidated and standalone, April-March fiscal year |
| News | Yahoo RSS and SEC 8-K | NSE/BSE announcements, SEBI, RBI, government, licensed media |
| Politics | US House PTRs | No direct equivalent; use insider/SAST/bulk-deal/flow data instead |

### 5.2 Component replacement matrix

| Component | Current source or assumption | India replacement | Effort | Risk |
| --- | --- | --- | --- | --- |
| Scanner universe | Nasdaq Trader symbol lists | NIFTY 50 constituent master, then NIFTY 100/500; NSE series and ISIN | Medium | Medium |
| Scanner data | Yahoo spark and chart | Licensed/broker NSE/BSE intraday and daily data; offline adapter for tests | High | High |
| Session calendar | NYSE 2026-2027 hardcoded | Shared IST/NSE/BSE calendar service with versioned holiday data | Medium | Medium |
| Symbol mapping | `.` to `-` | Canonical symbol to NSE/BSE/Yahoo/broker symbol mapping | Medium | High |
| Entry timer | Yahoo 5m/1m bars, ET window | Broker/vendor bars, IST, pre-open, circuits, MIS square-off | Medium | High |
| Exit planner | US cents, 15:55 flat-by | Rupee ticks, broker square-off, F&O lots, options premium | Medium | Medium |
| Risk engine | US tickers, PDT, NYSE window | SEBI/broker margins, T+1, ban list, price bands, Indian order types | High | High |
| Sizing | Whole shares, USD | Lots, margin, product codes, costs | High | Medium |
| Broker | Alpaca/IBKR MCP | Kite/Upstox/Angel/Dhan/Fyers adapter, token lifecycle, reconciliation | High | Very high |
| Alerts | Yahoo/Stooq, ET | Broker/vendor quotes, IST, real notification delivery | Medium | Medium |
| News | Yahoo RSS/SEC | NSE/BSE/SEBI/RBI/licensed news, entity linking, sentiment | High | High |
| Fundamentals | SEC XBRL | NSE/BSE XBRL, Ind AS, consolidated/standalone | High | Medium |
| Political tracker | US House PTRs | Not applicable; repurpose ingestion for insider/flow data | Low | Low |
| Time Machine | 78-bar ET session, Yahoo 60d | 75-bar IST session, licensed history, costs, event calendar | Medium | High |
| Backtesting | None (Time Machine only) | Event-driven engine with costs, slippage, walk-forward | Very high | High |

### 5.3 India-specific rules and product decisions to settle before coding

1. **Universe:** NIFTY 50 only initially, or NIFTY 100/500? How to handle index reconstitution and symbol changes?
2. **Equity product:** cash delivery (CNC) or intraday (MIS)? If MIS, which broker and what square-off time?
3. **Options mode:** NIFTY weekly and monthly only, or stock options too? European-style index options versus American-style stock options? Cash settlement versus physical settlement?
4. **Data:** real-time, delayed or end-of-day? Which vendor or broker? What are the licensing and redistribution terms?
5. **Execution:** human-in-the-loop forever, or eventual automation? If automation, SEBI algo registration and broker approval are gating items.
6. **Compliance:** personal research tool, advisory product, or fund? The answer changes SEBI RA/IA and recordkeeping obligations.
7. **Costs:** which statutory and broker charges must be modelled per trade? The backtest and recommendation layer should use the same cost model as live.
8. **Risk limits:** capital, max loss per trade, daily loss, max positions, sector and correlation caps, margin buffer.
9. **Timeframes:** 1m, 5m, 15m, 30m, 1h, daily? Which timeframes are used for signals versus confirmation?
10. **Outcome definition:** what counts as success for the learning loop? Target-first, positive R at flat-by, or net-of-cost P&L after a fixed horizon?

---

## 6. Missing components needed for our vision (E)

### 6.1 Data and instrument foundation

- **Licensed NSE/BSE data ingestion:** real-time or delayed quotes, 1m/5m/15m/1h/daily bars, index data, options chain, corporate actions, announcements.
- **Instrument master:** canonical symbol, ISIN, NSE/BSE codes, series, lot size, tick size, expiry, strike, option type, sector, index membership, free float and weights.
- **Corporate-action adjustment:** splits, bonuses, dividends, mergers, symbol changes.
- **Storage:** time-series store (Parquet plus DuckDB, TimescaleDB or ClickHouse) with immutable snapshots and data-quality flags.
- **Data quality:** gap detection, duplicate bars, stale quotes, outlier checks, session alignment, vendor reconciliation.

### 6.2 Feature and signal engine

- **Indicators:** VWAP, EMA/SMA across multiple periods, RSI, MACD, Bollinger Bands, ATR, ADX, Supertrend, OBV, volume profile, pivots, support/resistance, breakout and reversal detection.
- **Candlestick patterns:** engulfing, hammer, doji, morning/evening star, inside/outside bar, and their reliability statistics.
- **Relative strength:** versus NIFTY 50, versus sector, versus own history.
- **Market context:** breadth, advance/decline, India VIX, sector rotation, FII/DII flows, index futures basis.
- **Timeframe selection:** dynamic selection of relevant timeframes; signal fusion and conflict resolution.

### 6.3 Recommendation layer

- A formal recommendation schema: instrument, mode (equity or options), direction, entry trigger, stop, targets, risk/reward, holding duration, confidence, expected value, invalidation, rationale, data timestamp and model version.
- **Selectivity:** a "no trade" decision must be a first-class outcome; quality beats quantity.
- **Confidence calibration:** probabilities must be calibrated against realised outcomes, not invented.
- **Explainability:** every recommendation should show the features and rules that produced it.
- **No guarantees:** language and UI must never promise profits.

### 6.4 Backtesting and validation

- Event-driven backtester with realistic fills, costs, slippage, latency and liquidity constraints.
- Walk-forward and out-of-sample testing; purged and embargoed cross-validation for time series.
- Multiple-testing correction; deflated Sharpe or similar; benchmark comparison.
- Regime analysis (trend, range, high volatility, event days, expiry days).
- Monte Carlo and stress tests, including gap and circuit scenarios.
- Reproducible experiment tracking (data snapshot, code version, parameters, results).

### 6.5 Trade journal and learning loop

- **Recommendation ledger:** every recommendation, whether or not it was executed.
- **Execution ledger:** orders, fills, partial fills, cancellations, slippage, costs.
- **Outcome labels:** target first, stop first, neither, R multiple, net P&L, holding time, maximum adverse excursion, maximum favourable excursion.
- **Counterfactuals:** what would have happened without the trade, or with a different stop/target.
- **Feature store and model registry:** versioned features, labels, models and evaluation reports.
- **Shadow mode and drift monitoring:** new models run alongside the current logic before promotion.
- **Human approval gate:** no model promotion or live risk increase without review.

### 6.6 Risk, portfolio and options

- Portfolio-level exposure, correlation, sector and factor caps.
- Margin and buying-power model per broker and product.
- Options: chain ingestion, implied volatility, Greeks, lot sizing, payoff, margin, expiry calendar, settlement, assignment/exercise, liquidity filters.
- Separate risk limits for equity and options; no mixing of the two modes.
- Kill switch, daily loss stop, order-rate limits and anomaly detection.

### 6.7 Execution and operations

- Broker abstraction with a common order model, idempotency keys, retries, reconciliation and order-state machine.
- Hard approval service outside the LLM; signed or tokenised approvals.
- Secrets management, authentication, role-based access and immutable audit logs.
- Observability: structured logs, metrics, traces, alerting and dashboards.
- CI/CD, unit/integration/replay tests, staging environment and disaster recovery.
- Notification channels for alerts and recommendations.

### 6.8 News, sentiment and fundamentals for India

- NSE/BSE corporate announcements, SEBI, RBI, government releases, exchange circulars.
- Licensed news feeds and event calendars (earnings, board meetings, dividends, splits, index changes).
- Entity linking, deduplication, source reliability and importance ranking.
- Sentiment model with an India-specific evaluation set; not just keyword tags.
- Earnings and fundamentals from NSE/BSE XBRL, Ind AS, consolidated and standalone.
- Prompt-injection defences for untrusted text.

### 6.9 Compliance and product

- SEBI research analyst and investment adviser rules if recommendations are offered to others.
- SEBI retail algo framework and broker approval if orders are automated.
- Data licensing and redistribution terms.
- Recordkeeping, audit trail, disclaimers and user education.
- Clear separation between research, recommendation and execution.

---

## 7. Technical risks and limitations (F)

### 7.1 Severity summary

| Risk | Severity | Evidence and impact |
| --- | --- | --- |
| Data licensing and reliability in India | High | The repo relies on free, unofficial Yahoo data; NSE/BSE data is licensed and redistribution is restricted. A product needs a vendor/broker agreement. |
| SEBI compliance for advice and algo execution | High | The repo is a personal tool with disclaimers; an Indian product that recommends or automates trades may trigger RA/IA and algo rules. Legal review is mandatory. |
| Execution safety depends partly on prompts | High | `ticket.py` never contacts a broker; the LLM does. The hard barrier is MCP permission, not a deterministic execution service. Prompt injection via news is a real vector. |
| No cost model | High | The backtest, Time Machine, sizing and risk ignore STT, exchange fees, GST, stamp duty, brokerage and slippage. Frequent trading can be dominated by costs. |
| Methodology overfitting | High | Only a handful of hand-built setups; the Time Machine uses about 59 sessions and an iid bootstrap; no walk-forward or multiple-testing control. |
| Calendar and session hardcoding | Medium | Six copies of a US calendar, years 2026-2027 only, ET DST. India needs a shared IST/NSE/BSE service with a versioned holiday source. |
| Symbol and instrument mapping | Medium | `replace(".", "-")` breaks Yahoo `.NS`; `TICKER` regex rejects many NSE symbols; no ISIN, lot size or series. |
| File-based state and concurrency | Medium | No locking, no transactions, no schema versioning; concurrent loops can race. |
| Unofficial data quality | Medium | Yahoo can lag, change, rate-limit or omit bars; no vendor SLA; no adjustment for corporate actions. |
| Test coverage gaps | Medium | Strong unit/CLI tests exist, but there are no live integration tests, no backtester validation, no data-quality tests and no performance tests. Tests were not run in this audit. |
| XML/PDF parsing security | Medium | `xml.etree.ElementTree` on untrusted feeds and `pdftotext` on downloaded PDFs; harden with `defusedxml`, validation and sandboxing. |
| Single-user, single-machine design | Medium | No auth, no multi-user, no scheduler, no monitoring; a sleeping laptop pauses watches. |
| Options absent | High for the options mode | No chain, Greeks, IV, lots, margin or expiry logic. This is a new subsystem. |
| Self-learning absent | High for the long-term vision | No labels, features, models, registry, shadow mode or drift monitoring. |
| Reproducibility | Low/Medium | Seeded simulation helps, but input data is not snapshotted; vendor revisions can change results. |
| Python 3.8 and no typing | Low | Deliberate compatibility, but modern tooling and type checking would improve maintainability. |
| License and attribution | Low | MIT permits reuse; keep the notice if code is copied. |

### 7.2 Specific code-level findings

1. **Provider symbol mapping is US-centric.** `to_yahoo()` in `scan.py:270-271`, `yahoo_symbol()` in `entry.py:230-231`, and similar helpers in `timemachine.py:188-190` and `alerts.py:200-201` replace dots with dashes. That is correct for US class shares (`BRK.B` to `BRK-B`) but wrong for Yahoo NSE suffixes (`RELIANCE.NS`). Use an explicit mapping table, not string replacement.
2. **Indian tickers fail the risk validator.** `check.py:87` allows 1-5 letters plus an optional one- or two-letter suffix. `RELIANCE.NS`, `HDFCBANK.NS`, `M&M.NS` and many others fail. Replace with an instrument-master lookup.
3. **Options validation is US-specific.** `OCC` at `check.py:86` matches US OCC option symbols, not NSE option identifiers. Build a separate option-instrument parser.
4. **The session is hardcoded.** `timemachine.py:86-88` uses `SESSION_BARS=78`, `OPEN_MIN=570`, `CLOSE_MIN=960`. India needs 75 bars, `OPEN_MIN=555`, `CLOSE_MIN=930`, plus pre-open handling. Similar constants exist in the scanner, entry, exit, risk and alerts tools.
5. **The calendar is hardcoded and duplicated.** `NYSE_HOLIDAYS` and `NYSE_EARLY_CLOSE` appear in six tools. Extract one shared calendar module driven by versioned data, not code copies.
6. **Entry range can be partial.** `entry.py:482-499` computes the opening range from whatever range bars are present. The scanner's `usable()` at `scan.py:610-619` rejects a chart with a missing bar. Decide the intended behaviour and make it consistent. A missing bar can be a halt, a thin stock or a data gap, and a partial range can create a false signal.
7. **Time Machine is conditioned on entry.** `simulate()` at `timemachine.py:349-424` starts at the entry price. It does not estimate the probability that the setup triggers. It also uses independent draws, ignores costs and uses about 59 sessions. Treat it as a diagnostic, never as validation.
8. **History replay is narrower than the live rule.** `history_replay()` at `timemachine.py:451-490` applies the opening-range setup only and does not apply the live volume filter or entry-window rules. The docs disclose that it skips non-ORB setups, but the difference should be explicit in any report.
9. **No corporate-action adjustment.** Daily and intraday scans use raw closes and highs/lows. A split or bonus inside the lookback window can distort RSI, moving averages, breakouts and the Time Machine pool.
10. **No cost model anywhere.** `size.py` computes max loss at the stop only; `check.py` checks risk at the stop only; `timemachine.py` computes R without fees or slippage. For Indian intraday, this can turn an apparent edge into a loss.
11. **The broker gate is advisory in Python.** `ticket.py` records approvals and fingerprints, but it does not place orders. The LLM calls the broker MCP tool. The hard gates are the user's yes and Claude's permission card. Our execution service must enforce approval and idempotency independently.
12. **Local state can be edited or stale.** `portfolio.json`, `state/broker.json` and `prices.json` are plain JSON. There is no signature, reconciliation or immutable log. Risk decisions are only as good as these files.
13. **No CI configuration.** There is no GitHub Actions or equivalent. Tests are run manually. The repo does include a strong offline test suite, which is a good starting point.
14. **XML and PDF attack surface.** `news.py` parses RSS/Atom with `xml.etree.ElementTree`; `ptr.py` shells out to `pdftotext` on downloaded PDFs. Harden parsers, validate content types and sizes, and sandbox subprocesses.
15. **Data freshness is heuristic.** Risk uses quotes under 15 minutes old (`check.py:90`, `FRESH_MINUTES=15`). That is reasonable for sizing, but not for timing an entry in a fast market.
16. **No schema versioning in the file contract.** Adding fields is easy, but changing semantics silently can break downstream skills. Use versioned schemas and validation in our system.
17. **No portfolio-level risk.** The risk engine is per-order and per-day. It does not model correlated positions, sector concentration, or aggregate Greeks. This matters even for a NIFTY 50 intraday book.
18. **No benchmark or relative performance.** The system never compares a setup's outcome to NIFTY 50 or to a random-entry baseline. The learning loop will need both.
19. **The "confidence" concept is absent.** The Time Machine gives probabilities for one plan; the rest of the system gives PASS/BLOCK. There is no calibrated confidence score or expected value.
20. **The docs are honest, which is a strength.** The README and skills repeatedly warn about simulation, stops, gaps, data delays and losses. We should preserve this tone and not let a future AI layer turn it into marketing.

### 7.3 Methodology critique of the Time Machine

- **Conditional probability, not trade probability.** It answers "if I am already in at this price, what happens next?" It does not answer "how often does this setup trigger, and is the trigger itself informative?"
- **IID bootstrap.** Sampling bars independently from the same time of day preserves the intraday volatility shape but destroys autocorrelation and volatility clustering. Real markets have runs, feedback and regime shifts.
- **Small pool.** About 59 sessions is a small sample for tail risk. A 10,000-path simulation creates precision, not new information.
- **No costs.** The break-even share `1/(1+R)` ignores brokerage, STT, exchange fees, GST, stamp duty and slippage. At 1R, a small cost can move the break-even threshold materially.
- **Stop-first assumption.** When a bar touches both stop and target, it counts as a stop. This is conservative, but it is an assumption, not a fact; intrabar path matters.
- **No event conditioning.** Earnings, RBI policy, budget, expiry, index rebalancing and global risk-off days can break the historical analogy.
- **No multiple-testing control.** If many setups and parameters are tried, the best-looking replay is likely to be luck.
- **Verdict thresholds are heuristic.** The 5-point and 15-point bands are reasonable communication aids, not statistical tests.
- **Best use:** a sanity check and a teaching tool. Not a promotion gate. A real promotion gate needs an event-driven backtest with costs, walk-forward validation and a benchmark.

### 7.4 What the repository does well

- Clear separation between deterministic tools and LLM orchestration.
- No third-party dependencies; easy to read and audit.
- Extensive offline tests and fixtures.
- Strong safety posture: paper by default, explicit approval, exit protection, honest language.
- Good refusal messages and plain-language output.
- Atomic writes in several places.
- Seeded simulation for reproducibility.
- No secrets in the repository.
- MIT license, which permits reuse.

---

## 8. Recommended phased migration plan (G)

The plan assumes we keep the cloned repository as a **reference only** under `third_party/` and build our application in a new source tree. We should not modify the clone. We can copy small, well-understood functions with attribution, but the architecture should be ours.

### Phase 0 - Decisions, compliance and guardrails (1-2 weeks)

**Goal:** settle the constraints before writing code.

- Choose the initial broker and data vendor; confirm NSE/BSE data licensing and API terms.
- Legal/compliance review: SEBI RA/IA scope, retail algo framework, recordkeeping, disclaimers.
- Confirm paper-only for the foreseeable future; define what "approval" means and who can approve.
- Write architecture decision records: Python version, storage, deployment, UI/API, LLM role.
- Threat model: prompt injection, credential handling, order tampering, data poisoning.
- Preserve MIT attribution for any reused code.

**Exit criteria:** signed-off scope, vendor shortlist, compliance checklist, no real-money path.

### Phase 1 - India Market Core v0 (2-3 weeks)

**Goal:** make time, instruments and data unambiguous.

- Shared IST/NSE/BSE calendar module driven by versioned holiday data; sessions, pre-open, special sessions.
- NIFTY 50 instrument master: canonical symbol, NSE symbol, ISIN, series, lot size, tick size, sector, index weight.
- Canonical-to-provider symbol mapping (NSE, BSE, Yahoo, broker).
- Normalised bar schema (timestamp, open, high, low, close, volume, timeframe, source, quality flags).
- Data-provider interface with an offline fixture adapter and a read-only live adapter.
- Tests for calendar edges, symbol mapping, bar alignment and session boundaries.

**Exit criteria:** all 50 symbols resolve; 75 five-minute bars per normal session; deterministic offline tests; no network in unit tests.

### Phase 2 - Data feasibility and historical backfill (2-4 weeks)

**Goal:** prove we can get reliable, legal history before building strategies.

- Ingest at least 2 years of daily and intraday NIFTY 50 data (and NIFTY index data).
- Corporate-action adjustment and symbol-change handling.
- Data-quality report: coverage, gaps, duplicates, stale bars, outliers, session alignment.
- Snapshot the dataset with a version and checksum.
- Compare vendor/broker sources on a sample and document differences.

**Exit criteria:** coverage and gap thresholds agreed; reproducible snapshot; documented source limitations.

### Phase 3 - Indicators, features and scanner (3-4 weeks)

**Goal:** build the analytical vocabulary.

- VWAP, EMA/SMA, RSI, MACD, Bollinger, ATR, ADX, volume, support/resistance, pivots, breakout/reversal and candlestick patterns.
- Multi-timeframe feature computation with explicit as-of timestamps (no lookahead).
- Relative strength versus NIFTY 50 and sector.
- A scanner over NIFTY 50 with configurable rules; deterministic outputs.
- Hand-computed unit tests for every indicator; property tests for edge cases.

**Exit criteria:** no lookahead; indicator tests pass; scanner produces reproducible hit lists.

### Phase 4 - Recommendation, risk, sizing and journal (3-4 weeks)

**Goal:** produce a complete, auditable recommendation without execution.

- Recommendation schema: entry, stop, targets, risk/reward, holding duration, confidence, expected value, invalidation, rationale, data timestamp, version.
- India equity risk engine: max loss, daily loss, position and sector caps, price bands, ban list, T+1 and MIS constraints, margin buffer.
- Sizing with costs and lot sizes; separate option sizing later.
- Paper portfolio and trade journal; recommendation and execution ledgers.
- A "no trade" decision path.

**Exit criteria:** every recommendation has an invalidation and a risk number; paper-only; full audit trail.

### Phase 5 - Backtesting and validation (4-6 weeks)

**Goal:** replace the Time Machine as a promotion gate.

- Event-driven backtester with realistic fills, costs, slippage, latency and liquidity.
- Walk-forward, out-of-sample and purged cross-validation.
- Multiple-testing control, benchmark comparison and regime analysis.
- Monte Carlo and stress tests, including gaps, circuits and expiry days.
- Reproducible experiment tracking.

**Exit criteria:** no strategy promoted without out-of-sample, net-of-cost evidence; cost sensitivity documented.

### Phase 6 - Broker integration and paper execution (4-6 weeks)

**Goal:** connect to an Indian broker without risking real money.

- Broker adapter for one provider first; common order model; order-state machine.
- OAuth/token lifecycle, static IP, rate limits, idempotency and reconciliation.
- Paper/sandbox orders only; manual approval service outside the LLM.
- Kill switch, daily loss stop and anomaly detection.
- SEBI/broker algo approval checklist if automation is ever enabled.

**Exit criteria:** paper orders reconcile; duplicate prevention proven; kill switch tested; no live money.

### Phase 7 - India news, sentiment and fundamentals (4-6 weeks)

**Goal:** add the information edge.

- NSE/BSE announcements, SEBI/RBI releases, licensed news and event calendars.
- Entity linking, deduplication, source reliability and importance ranking.
- Sentiment model with an India-specific evaluation set.
- NSE/BSE XBRL fundamentals, Ind AS, consolidated/standalone.
- Prompt-injection defences and human review for ambiguous items.

**Exit criteria:** measured precision/recall on a labelled set; no trade on unverified headlines; source links retained.

### Phase 8 - Options mode (6-8 weeks)

**Goal:** add NIFTY options as a separate mode.

- Chain ingestion, implied volatility, Greeks, lot sizes, margin and payoff.
- Expiry calendar, settlement rules, assignment/exercise and liquidity filters.
- Separate risk limits, sizing and backtest assumptions.
- Expiry-day and event-day stress tests.

**Exit criteria:** paper options only; Greeks and margin reconciled to the broker; separate risk book.

### Phase 9 - Self-learning loop (ongoing)

**Goal:** improve through validated outcomes, not intuition.

- Feature store, label definitions and outcome tracking.
- Model registry, experiment tracking and versioning.
- Shadow mode, drift monitoring, explainability and rollback.
- Human approval before any model affects recommendations or risk.
- Continuous evaluation against baselines, including random entry and simple rules.

**Exit criteria:** a model beats a pre-registered baseline out-of-sample after costs, with monitored stability. Otherwise, it does not ship.

### Phase 10 - Hardening and productisation (ongoing)

- Observability, authentication, secrets management and audit logs.
- CI/CD, staging, replay tests and disaster recovery.
- UI/API, notifications and user education.
- Compliance review, disclaimers and recordkeeping.

**Sequencing rule:** do not start options or self-learning before the data, backtest and journal foundations are reliable. A sophisticated model on unreliable data is a liability.

---

## 9. Recommended first development task (H)

### Task: India Market Core v0 plus a data-feasibility spike

**Why this first:** every later component depends on correct time, correct instruments and trustworthy bars. Building indicators or signals before this would bake in symbol, calendar and data errors. This task also tests the single biggest external risk (Indian data availability and licensing) before we invest in strategy work.

**Scope (in):**

1. **Calendar module**
   - IST, UTC+05:30, no DST.
   - NSE/BSE equity session 09:15-15:30, pre-open 09:00-09:15, special sessions.
   - Versioned holiday data loaded from a JSON file with a source and retrieval date.
   - Functions: is trading day, session bounds, next open, is bar complete, is within entry window.
   - Unit tests for weekends, holidays, pre-open, session edges and year rollover.

2. **Instrument master**
   - NIFTY 50 constituents with canonical symbol, NSE symbol, ISIN, series, lot size, tick size, sector and index weight.
   - Canonical-to-provider mapping (at minimum NSE and one read-only data provider).
   - Versioned file with a source and effective date.
   - Unit tests for mapping, duplicates, missing fields and index changes.

3. **Normalised bar schema and provider interface**
   - A `Bar` model: symbol, timeframe, start timestamp in UTC and IST, open, high, low, close, volume, source, quality flags.
   - A `DataProvider` protocol with `get_bars(symbol, timeframe, start, end)`.
   - An offline fixture provider for tests.
   - A read-only live adapter (Yahoo `.NS` or broker sandbox) behind the interface, with caching and rate limiting.
   - No order placement, no credentials required for the offline path.

4. **Data-feasibility spike**
   - Fetch or obtain a sample of NIFTY 50 daily and 5-minute history from at least one candidate source.
   - Produce a short report: coverage, gaps, timestamps, session alignment, split/bonus issues, licensing constraints, and a recommendation.
   - Do not build strategies on it yet.

**Out of scope:** indicators, scanner, recommendations, broker orders, options, ML, UI.

**Acceptance criteria:**

- All 50 NIFTY 50 symbols resolve through the instrument master.
- A normal session yields 75 five-minute bars aligned to 09:15-15:30 IST.
- Calendar tests cover at least one holiday, one weekend, one pre-open boundary and one year rollover.
- Offline tests run with no network access and are deterministic.
- The data-feasibility report states clearly whether the candidate source is suitable, with evidence.
- No file in `third_party/day-trader-skill` is modified.
- No credentials, no broker connection and no orders.

**Deliverables:** source modules, versioned calendar and instrument JSON, offline fixtures, tests, and a short feasibility report. Then stop and review before Phase 2.

**Second task (after approval):** port the opening-range breakout and a small indicator set to NIFTY 50 on the normalised data, with a deterministic scanner and hand-computed tests. Still no execution.

---

## 10. Decisions required from you

Before Phase 1, please decide:

1. **Broker and data vendor:** which broker (Kite, Upstox, Angel One, Dhan, Fyers, other) and which data source? What is the budget for data?
2. **Real-time vs delayed:** do we need live intraday data, or is delayed/end-of-day acceptable for the first version?
3. **Equity product:** cash delivery, intraday MIS, or both? Which square-off time?
4. **Options scope:** NIFTY weekly/monthly only, or stock options too? Do we need Greeks and margin from day one?
5. **Compliance posture:** personal research tool, advisory product, or fund? This determines SEBI RA/IA and algo obligations.
6. **Execution model:** human-in-the-loop forever, or eventual automation? What is the paper-trading period?
7. **Stack:** Python version, storage (Parquet/DuckDB/SQLite/Postgres), deployment (local/cloud), and whether Claude remains the UI or we build our own.
8. **Universe and timeframes:** NIFTY 50 only or NIFTY 100/500? Which timeframes for signals and confirmation?
9. **Risk limits:** capital, max loss per trade, daily loss, max positions, sector/correlation caps, margin buffer.
10. **Outcome definition:** what label should the learning loop optimise? Target-first, net R at flat-by, or net P&L over a fixed horizon?
11. **Licensing:** are we allowed to store and redistribute vendor data internally? What are the retention rules?
12. **Whether to reuse code:** copy small MIT-licensed functions with attribution, or clean-room reimplement everything? My recommendation is a clean-room core with selective, attributed reuse of small algorithms.

---

## Appendix A - File inventory

| Folder | Files | Role |
| --- | --- | --- |
| `.claude-plugin` | `plugin.json`, `marketplace.json` | Claude plugin metadata |
| `trader-scanner` | `SKILL.md`, `scan.py` | Universe, daily setups, ORB scan |
| `trader-news` | `SKILL.md`, `news.py` | Headlines, 8-Ks, move detection |
| `trader-entry` | `SKILL.md`, `entry.py` | Bar-by-bar entry trigger |
| `trader-exit` | `SKILL.md`, `exit.py` | Stop/target plan |
| `trader-timemachine` | `SKILL.md`, `timemachine.py` | Monte Carlo and history replay |
| `trader-risk` | `SKILL.md`, `check.py` | Pre-trade risk gate |
| `trader-budget` | `SKILL.md`, `size.py`, `config.example.json`, `targets.example.json` | Sizing and order proposal |
| `trader-broker` | `SKILL.md`, `ticket.py`, `claude_desktop_config.example.json` | Ticket, approval, broker log |
| `trader-alerts` | `SKILL.md`, `alerts.py`, `alerts.example.json` | Price/time alerts |
| `trader-analyst` | `SKILL.md`, `facts.py`, `metrics.example.json` | SEC XBRL fundamentals |
| `trader-pelosi` | `SKILL.md`, `ptr.py` | US House PTR tracker |
| `tests` | 12 `test_*.py`, `_load.py`, `fixtures/` | Offline test suite |

## Appendix B - Key code references

| Topic | Reference |
| --- | --- |
| US calendar and sessions | `trader-scanner/scan.py:96-126`; `trader-entry/entry.py:74-104`; `trader-exit/exit.py:64-93`; `trader-timemachine/timemachine.py:99-104`; `trader-risk/check.py:94-124`; `trader-alerts/alerts.py:66-96` |
| US DST implementation | `trader-alerts/alerts.py:105-131` (duplicated in other tools) |
| Symbol mapping (dot to dash) | `trader-scanner/scan.py:270-271`; `trader-entry/entry.py:230-231`; `trader-timemachine/timemachine.py:188-190`; `trader-alerts/alerts.py:200-201` |
| RSI and daily setups | `trader-scanner/scan.py:485-539` |
| Opening-range scan | `trader-scanner/scan.py:584-644`; `trader-scanner/scan.py:686-737` |
| Entry state machine | `trader-entry/entry.py:408-552` |
| Opening-range completeness inconsistency | `trader-entry/entry.py:482-499` versus `trader-scanner/scan.py:610-619` |
| Stop/target arithmetic and ATR | `trader-exit/exit.py:270-333`; `trader-exit/exit.py:469-484` |
| Monte Carlo | `trader-timemachine/timemachine.py:335-424` |
| History replay | `trader-timemachine/timemachine.py:451-490` |
| Verdict logic | `trader-timemachine/timemachine.py:631-676` |
| Risk engine | `trader-risk/check.py:373-702` |
| US ticker and option regex | `trader-risk/check.py:86-87` |
| Risk window and PDT | `trader-risk/check.py:213-254`; `trader-risk/check.py:627-630` |
| Sizing | `trader-budget/size.py:305-415` |
| Bracket order shape | `trader-budget/size.py:418-441` |
| Fingerprint | `trader-risk/check.py:271`; `trader-broker/ticket.py:145-149` |
| Explicit-yes parser | `trader-broker/ticket.py:271-297` |
| Alert time rules | `trader-alerts/alerts.py:148-191`; `trader-alerts/alerts.py:428-494` |
| News feeds and dedupe | `trader-news/news.py:55-63`; `trader-news/news.py:381-434` |
| SEC XBRL concepts | `trader-analyst/facts.py:53-73`; `trader-analyst/facts.py:166-294` |
| House PTR parsing | `trader-pelosi/ptr.py:48-59`; `trader-pelosi/ptr.py:251-336` |
| Test invariants | `tests/test_repo.py:35-135` |
| Python 3.8 constraint | `tests/test_repo.py:103-119` |

## Appendix C - Verification notes

- The clone was created with `git clone --depth 1`, so the local clone has only the latest commit, not the full history. This does not affect the audit of the current code.
- The original repository was not modified; no Git configuration was changed.
- No Python script, shell script or repository-provided command was executed.
- No packages were installed.
- No broker, exchange or trading account was contacted.
- No API keys, passwords or credentials were requested, read or stored.
- The Time Machine fixture was inspected as data only: `TSLA-60d5m.json.gz` contains 4,619 timestamps across 60 distinct UTC dates from 2026-07-27 to 2026-10-19, consistent with 59 prior sessions plus the entry day.
- The repository's test suite was not run. Its structure and intent were reviewed.
- The only files created by this audit are the clone under `third_party/day-trader-skill` and this report. No existing project file was overwritten because the project directory was empty at the start.

## Appendix D - Glossary

| Term | Meaning |
| --- | --- |
| ORB | Opening-range breakout: the first N minutes of the session define a high and low; a close above the high is the long trigger |
| R | One unit of risk: entry minus stop for a long |
| ATR | Average True Range, a volatility measure |
| VWAP | Volume-weighted average price |
| MIS | Broker intraday product in India, usually squared off before the close |
| CNC | Cash-and-carry delivery product in India |
| T+1 | Settlement one business day after the trade |
| STT | Securities Transaction Tax in India |
| SPAN | Standard Portfolio Analysis of Risk, an exchange margin methodology |
| SEBI | Securities and Exchange Board of India |
| NSE/BSE | National Stock Exchange and Bombay Stock Exchange |
| PTR | Periodic Transaction Report, a US congressional disclosure |
| CIK | SEC Central Index Key |
| XBRL | eXtensible Business Reporting Language, used in SEC and Indian filings |
| PDT | US pattern-day-trader rule; not applicable in India |

---

**STOP.** This audit is complete. No implementation has begun. The next step is your review and approval of the plan, the first task, and the decisions listed in section 10.
