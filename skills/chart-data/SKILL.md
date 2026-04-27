---
name: chart-data
description: Pull and verify pure factual data from a live TradingView chart — key levels, unmitigated S&D zones, unmitigated FVGs, ICC structural levels — and write a per-symbol snapshot file. No analysis, no judgment, no trade-framework concepts. The snapshot is the single source of truth that downstream skills (chart-read) consume. Use when the user asks to refresh chart data, pull a new snapshot, or before running any analysis skill.
---

# chart-data — pure factual snapshot

This skill exists for one job: extract verified factual data from a live TradingView chart and persist it to a markdown snapshot. Nothing else.

**Hard rule:** if a step requires interpretation, judgment, classification beyond a deterministic comparison, or any trade-framework concept (entry, stop, risk, R-multiples, "fresh," "the magnet," grade, Call, trend, phase) — that step does not belong here. It belongs in `chart-read`.

A snapshot is consumed by `chart-read` to produce playbooks. If chart-data is wrong, every downstream report is wrong. Verification gates below are not optional.

## Vocabulary (limited on purpose)

- **Key level:** a single price marked by the `ICT Killzones & Pivots [TFO]` indicator (PDH/PDL/PWH/PWL/PMH/PML/D Open/W Open/M Open).
- **EQ level:** the midpoint of a paired high/low (PD-EQ = (PDH+PDL)/2; PW-EQ; PM-EQ). Derived inline.
- **Sweep status:** `alive` (session range never touched the level), `alive · wick-tested` (session high/low equals the level within 1 tick — touched but not traded through), `taken` (session range cleanly traded through the level by more than 1 tick).
- **Zone:** an unmitigated rectangle from the `Market Structure CHoCH/BOS (Fractal) [LuxAlgo]` indicator. Two price edges (upper, lower) plus a direction (supply or demand). Nothing else.
- **FVG:** an unmitigated box from `FVG/iFVG (Nephew_Sam_)`. Three indicator instances on the chart, one per timeframe.
- **ICC structural levels:** ind (most recent broken pivot in the current cycle), TP (the leg extreme after ind broke; "forming" if no pivot has crystallized), inv (the PLH/PHL one back from the most recent in the current cycle). Numeric values only — no phase classification here.

## Prerequisites

Chart must have these indicators visible:
- `ICT Killzones & Pivots [TFO]`
- `Market Structure CHoCH/BOS (Fractal) [LuxAlgo]`
- `FVG/iFVG (Nephew_Sam_)` (one or more instances)

Verify with `chart_get_state` at the start of the run. If any are missing, stop and tell the user — do not guess at indicator names.

## Default symbols & within-point caps

| Symbol | within_points |
|---|---|
| MNQ1! (CME_MINI:MNQ1!) | 400 |
| MES1! (CME_MINI:MES1!) | 100 |
| MGC1! (COMEX:MGC1!) | 50 |
| SIL1! (COMEX:SIL1!) | 5 |

Caps are tuned per instrument volatility. If the user passes a custom symbol, ask for the cap before running.

## Verification gates (mandatory)

Run as silent preconditions. A failed gate either retries, falls back to the OHLCV-derived value, or skips the symbol with a documented reason. Never publish a snapshot with a failed gate.

1. **Indicator-stable.** After `chart_set_symbol`, sleep ≥5s. Pull labels twice with a 2s gap. Values must match across both pulls. If they don't, sleep again and re-pull until two consecutive pulls are identical. Same drill for `data_get_structure_zones` and `data_get_pine_boxes`.

2. **Period-label OHLCV cross-check.** For each PMH/PML/PWH/PWL/PDH/PDL pulled from the indicator: pull a small OHLCV slice covering the corresponding prior period (PDH/PDL → prior trading day; PWH/PWL → prior calendar week; PMH/PML → prior calendar month) and compute the period high/low. Indicator value must match within 1 tick. If mismatch, the indicator is mis-configured for that boundary — use the OHLCV-derived value in the snapshot, with a flag note: `(indicator returned X; cross-check shows Y; using Y)`.

3. **Session window correctness.** Compute the current futures session start in ET:
   - Sunday between 18:00 ET and Monday session close → session start = Sunday 18:00 ET
   - Monday–Friday → session start = prior trading day 18:00 ET (or this morning if mid-day)
   - Holiday-adjusted per `reference_market_holidays` memory
   `count = ceil(hours_elapsed_since_session_start × 4)` for 15m OHLCV. Sanity-verify: first bar's open in the OHLCV must equal indicator's `D OPEN` within 1 tick. If not, the window is wrong — recompute and re-pull.

4. **Sweep test stated, with wick-tag exception.** For each label, compute and record the comparison:
   - Label above current price + session_high > label by more than 1 tick → `taken`
   - Label above current price + session_high == label (within 1 tick) → `alive · wick-tested`
   - Label above current price + session_high < label → `alive`
   - Mirror for below-price labels (using session_low)
   Every snapshot entry for a label must include the comparison numbers in parentheses. Bare `(taken)` without the comparison fails review.

5. **Cross-pull drift alarm.** If any indicator value (label price, zone edge, FVG box, color) differs between two pulls in the same run, both pulls are suspect. Wait, re-pull, document the drift in a snapshot footnote, and use the value from the most recent stable pair.

6. **Zone geometry sanity.** Pull `data_get_structure_zones` returns `entry`, `sl`, `direction`. For supply zones, the broken-pivot price (the zone's lower price boundary) must be < the paired-pivot price (upper boundary). For demand, mirror. **In the snapshot, do not preserve the indicator's `entry` / `sl` field names** — these are framework-loaded. Output `upper` and `lower` price edges only. If geometry contradicts the `direction` field, skip the zone and log: `zone {bar_idx} skipped — geometry/direction mismatch`.

7. **FVG color decode.** Decode `borderColor` as ABGR: mask the high alpha byte, the low three bytes are RGB.
   - Bullish FVG: green-dominant (e.g. RGB ≈ (0, 230, 118)) — call this `bullish`
   - Bearish FVG: red-dominant (e.g. RGB ≈ (242, 54, 69)) — call this `bearish`
   - iFVG: teal/blue/orange intermediate hue — call this `iFVG`
   Every FVG snapshot entry must carry an explicit direction tag. iFVGs are included in the snapshot but flagged for skip downstream.

8. **ICC anchored to current cycle.** After pulling 4h `data_get_structure_zones` with `include_mitigated: true`, sort by `bar_idx` descending. The most recent BOS/ChoCh in the cycle direction defines the cycle.
   - **ind** = the broken pivot price of the most recent cycle-defining event. For a bear cycle with a recent bear BOS at `entry = X`, `ind = X`.
   - **inv** = the dashed-pivot (paired) price of the BOS/ChoCh one back from the most recent in the same cycle direction. Do not pluck inv from older same-direction events that have been superseded by the current cycle.
   - **TP** = the leg extreme after ind broke. Pull ~15 bars of 4h OHLCV after the ind-break bar; the lowest low (bear) or highest high (bull) is the candidate. If the candidate has at least 5 bars on each side without violating it, it has crystallized as a pivot — use the numeric value. If not, use `forming` and record the working extreme separately.

## Workflow per symbol

Budget: ≤ 14 MCP calls per symbol on a typical run. The verification gates may trigger re-pulls; a thorough run can reach 20+ calls.

### Setup

1. `tv_health_check` once at the start.
2. `chart_get_state` once to verify required indicators are present.

### Per-symbol pass

1. `chart_set_symbol` → sleep 5s
2. `chart_set_timeframe 240` → sleep 2s
3. Pull `data_get_pine_labels` (study_filter: "ICT Killzones") — first pull
4. Sleep 2s
5. Pull `data_get_pine_labels` again — verify match (Gate 1)
6. Pull `data_get_structure_zones` (study_filter: "Market Structure", `within_points` per symbol cap, `include_mitigated: true`) — for ICC derivation and to anchor unmitigated 4h zones
7. Pull `data_get_pine_boxes` (study_filter: "FVG", `verbose: true`) — 4h FVGs
8. Pull `data_get_ohlcv` (count: 15, summary: false) — 4h bars for ICC TP pivot detection
9. `chart_set_timeframe 15` → sleep 2s
10. Pull `data_get_structure_zones` (within_points per symbol cap, default `include_mitigated: false`) — 15m unmitigated zones
11. Pull `data_get_pine_boxes` (study_filter: "FVG", `verbose: true`) — 15m FVGs
12. Compute Gate 3 session window. Pull `data_get_ohlcv` (count = ceil(hours_since_session_start × 4), summary: true) — session range
13. **Period cross-check pulls (Gate 2).** Switch to D timeframe (`chart_set_timeframe D`), pull `data_get_ohlcv` (count: 30, summary: false) → derive PDH/PDL from yesterday's bar, PWH/PWL from prior week's bars, PMH/PML from prior month's bars. Cross-check vs indicator labels.
14. Decode FVG colors (Gate 7). For each FVG, compute untouched status by comparing `[low, high]` against bar range from `x1` forward (use existing 15m / 4h OHLCV bars; if creation is older than the OHLCV window, mark `untouched_check: indeterminate` and do not claim untouched).
15. Compute label sweep statuses (Gate 4) and EQ midpoints + their sweep statuses.
16. Identify ICC ind/TP/inv per Gate 8.
17. Write the snapshot file.

After the per-symbol pass, restore the chart timeframe to 240 (4h) before moving to the next symbol — leaves the chart in a consistent state.

## Snapshot output template

**Filename:** `analysis/data/YYYY-MM-DD-HHMMET-{SYMBOL}.md` (24-hour, ET suffix; symbol without `1!` suffix or exchange prefix).

**Format:**

```markdown
# chart-data snapshot — {SYMBOL}

**Captured:** {YYYY-MM-DD HH:MM ET}
**Current price:** {price}
**Chart TF at capture:** {15m or 240}

## Session window

- Session start: {YYYY-MM-DD HH:MM ET}  ({rationale: e.g., "Sunday 18:00 ET — new futures week"})
- Bars pulled (15m): {count}
- Session open: {price}  (vs indicator D OPEN {price} — match within 1 tick: yes/no)
- Session high: {price}
- Session low: {price}

## Key levels

| Level | Value | Source check | Side | Sweep status |
|---|---|---|---|---|
| PDH | {price} | indicator + OHLCV match (within tick) | above/below | alive / alive · wick-tested / taken (session_high {value} vs label {value}) |
| PDL | ... | ... | ... | ... |
| PWH | ... | ... | ... | ... |
| PWL | ... | ... | ... | ... |
| PMH | ... | ... | ... | ... |
| PML | ... | ... | ... | ... |
| D Open | ... | indicator only (no prior-period check) | ... | ... |
| W Open | ... | indicator only | ... | ... |
| M Open | ... | indicator only | ... | ... |

If a level fails Gate 2 (indicator vs OHLCV mismatch), use the OHLCV value and add a footnote: `* PMH: indicator returned X; OHLCV-derived March high was Y; using Y.`

## Derived EQ levels

| Level | Value | Side | Sweep status |
|---|---|---|---|
| PD-EQ | {(PDH+PDL)/2} | ... | ... |
| PW-EQ | {(PWH+PWL)/2} | ... | ... |
| PM-EQ | {(PMH+PML)/2} | ... | ... |

## Unmitigated S&D zones — 15m

| Upper | Lower | Direction | bar_idx |
|---|---|---|---|
| {price} | {price} | supply / demand | {n} |

If none within `within_points` of price, write: `none within {cap} pts of price`.

## Unmitigated S&D zones — 4h

Same format as 15m.

## Unmitigated FVGs — 15m

| Low | High | Direction | x1 | Untouched |
|---|---|---|---|---|
| {price} | {price} | bullish / bearish / iFVG | {bar offset} | yes / no / indeterminate |

iFVGs included for completeness; downstream skills skip them.

## Unmitigated FVGs — 4h

Same format. (1h FVGs included if a 1h-tuned indicator instance is present.)

## ICC structural levels (4h)

- **ind:** {price} — broken pivot price of the most recent {bear / bull} cycle-defining event (bar_idx {n})
- **TP:** {price or "forming"} — {leg extreme description; if "forming," include working extreme value as a note}
- **inv:** {price} — paired pivot of the cycle event one back from the most recent (bar_idx {n})

## Notes / drift / failed gates

If any gate triggered a retry, fallback, or skip, document it here. Empty if everything passed cleanly.
```

## Rules (no exceptions)

1. **No analysis vocabulary.** No "magnet," "fresh," "stacked," "the trade," "entry," "stop loss," "SL," "risk," "tp_3R," "R-multiple," "grade," "Call," "GO LONG," "GO SHORT," "trend," "phase," "Indication," "Correction," "Continuation," "cluster," "confluence." If any of these words appear in a chart-data snapshot, the skill ran wrong.

2. **No prose.** The snapshot is tables and bullet lists only. No "the day wants to," no "watching for," no narrative. Just data.

3. **Two prices and a direction.** That's all a zone gets. No `entry`, no `sl`, no `risk`. The trader's invalidation point is not a fact about the chart.

4. **Sweep status is for points, not ranges.** Labels and EQ levels carry sweep status. Zones do not — they are unmitigated or mitigated per the indicator, full stop.

5. **Every cited number is verified.** No exceptions. If a value can't be verified (e.g., indeterminate untouched-check), say so explicitly — never guess.

6. **Snapshot per symbol per run.** Multiple snapshots per day are expected. Filename includes the timestamp so chart-read can pick the latest and detect staleness.

7. **Restore chart state.** Leave the chart on 4h after each per-symbol pass so the next symbol starts predictably.

8. **If a verification gate cannot be satisfied, the snapshot is incomplete.** Record the failure in the Notes section and surface it to the user — do not paper over.

9. **Live chart authority — never back-fill from prior snapshots.** The chart at pull time is the only source of truth. If a value cannot be obtained from this run's tool calls (e.g., a D-bar pull came back in summary mode and missed PWH/PMH, a structure_zones pull returned fewer events than expected), the correct response is to re-pull on this run — not to reach into a prior snapshot file and copy the old value. Indicator parameters (LuxAlgo `length`, killzone session windows, FVG settings) are user-controlled and can change between runs; when they do, the indicator legitimately re-evaluates its entire event list and the snapshot must reflect the new state. Similarly, do not frame between-run changes as "drift" or "differs from prior" in the Notes section — the chart now says X, full stop. The Notes section should describe this run's state, not narrate deltas against past runs.

10. **Re-pull, don't substitute.** If a pull returns partial or summary data when full data was expected, the next action is another pull on the same TF/symbol — never a backfill from a different timestamp's snapshot. A snapshot that depends on values from a prior file is not a clean snapshot of the current chart and is barred from chart-read consumption.
