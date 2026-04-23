# Metal Bullet Strategy — MGC / SIL 21:00–22:00 ET

**Shanghai AM kill-zone. 1-minute execution. Structure-confirmed entries via LuxAlgo Market Structure Fractal.**

---

## Scope

This is a standalone overnight strategy. It is **not** part of ICC, S&D, or Silver Bullet, and does not compose with them. Do not apply it to MNQ, MES, ES, NQ, or any other instrument — MGC and SIL only.

| Parameter | Value |
|---|---|
| Instruments | MGC (Micro Gold) · SIL (Micro Silver) |
| Session window | **21:00–22:00 ET** (hard bounds) |
| Execution timeframe | 1 minute |
| Indicator | LuxAlgo — *Market Structure CHoCH/BOS (Fractal)*, **period = 3 bars each side** |
| Position size | **MGC 3 contracts · SIL 2 contracts** (default for dollar-risk parity) |
| Risk:Reward | Fixed **2R** (2:1) |

The 21:00–22:00 ET window corresponds to **Shanghai AM open** — the Asia session's kick-in for precious metals. China is the largest physical gold and silver consumer globally, and Shanghai AM is consistently one of two tradeable windows in the overnight session where hourly range matches RTH (the other being London/Europe open at 07:00–09:00 ET). The edge thesis: by 21:00 ET, Asia traders are at desks, Shanghai Gold Exchange is open, and the session often prints its cleanest overnight structural leg inside this hour. Outside this window, metals often drift in low-conviction price action.

---

## The Indicator

**LuxAlgo — Market Structure CHoCH/BOS (Fractal)** plots swing fractals and labels every fractal break as one of two events:

- **BOS (Break of Structure)** — price breaks a fractal in the direction of the prevailing structure. Continuation signal.
- **CHoCH (Change of Character)** — price breaks a fractal *against* the prevailing structure. First sign of a potential reversal. A CHoCH is always the first counter-trend break; subsequent same-direction breaks are BOS.

**Indicator settings — critical:** Run the indicator with **period = 3 bars on each side** (a 7-bar fractal), not the default 5. Institutional moves during the 21–22 window — especially Shanghai-driven impulses — are fast and often trend continuously. At 5-each-side, would-be fractals get invalidated by the next higher high / lower low before they're confirmed, and the indicator silently skips structural breaks that are happening in real time. 3-each-side is fast enough to keep up with the window's pace without being so loose that noise fires labels.

**Label timing — critical:** A BOS or CHoCh label **only appears at the moment of break confirmation**. The label stamps the **break bar**, not the fractal bar — i.e., the label's time is when price actually took out the prior swing, not when the swing itself formed. This is the bar we use for setup timing and entry.

**Line conventions on the indicator:**

- **Solid line** — drawn at the broken fractal level (the level price just took out). This is the *event* price.
- **Dashed line** — drawn at the opposite confirmed fractal that formed since the break. This is the structural invalidation reference — the level that, if broken, would invalidate the new direction.

The dashed line is what we use as the **stop loss**.

---

## The Setup

An entry requires **two consecutive same-direction structure events**, both printed by the indicator **inside the 21–22 window**. Exactly two valid sequences:

### Sequence A — CHoCH → BOS

A character shift followed by a confirming continuation.

1. A CHoCH prints in the window (e.g., bullish CHoCH = price breaks a prior down-fractal high).
2. A BOS prints in the same direction, after the CHoCH, also inside the window.
3. Enter on/after the BOS confirmation.

### Sequence B — BOS → BOS

Two same-direction continuations with no intervening CHoCH.

1. A BOS prints in the window in a given direction.
2. A second BOS prints in the same direction, after the first, also inside the window.
3. Enter on/after the second BOS confirmation.

**Both events must be:**
- Same direction (both bullish **or** both bearish).
- Confirmed (not forming) — the fractal must be closed and the break must have printed its label on the indicator.
- Stamped inside the window — the timestamp of each break must fall between 21:00:00 and 21:59:59 ET.

Mixed sequences are **not** valid setups:
- BOS → CHoCH (opposite direction by definition) — no.
- CHoCH → CHoCH in the same direction — cannot happen; the second break is a BOS by indicator logic.
- CHoCH → CHoCH in opposite directions — whipsaw, no trade.

MGC and SIL are evaluated **independently**. A valid setup on one does not gate the other.

---

## Entry, Stop, Target

| Component | Rule |
|---|---|
| **Entry** | Market entry at/after the bar close that prints the second (confirming) structure event. |
| **Stop loss** | The **dashed line** the indicator shows corresponding to the triggering structure event — i.e., the opposing confirmed fractal. For a long: the dashed low below price. For a short: the dashed high above price. Do not use a fixed tick offset. |
| **Take profit** | **2R** — distance from entry to stop, multiplied by 2, projected in the trade direction. |
| **Size** | MGC 3 contracts · SIL 2 contracts (default — see contract values below). |

Stops and targets are both structural-to-fixed: SL is anchored to indicator structure, TP is a fixed multiple of that structural risk.

### Contract values

| Instrument | Contract size | Tick | Tick $ | Point $ (per contract) |
|---|---:|---:|---:|---:|
| MGC | 10 troy oz | 0.10 | $1.00 | **$10** |
| SIL | 1,000 troy oz | 0.005 | $5.00 | **$1,000** |

SIL's per-point exposure is 100× MGC's. Default sizing for dollar-risk parity: **MGC 3 contracts · SIL 2 contracts**. Under that sizing: a 3-contract MGC with 15 pt SL risks $450; a 2-contract SIL with 0.30 pt SL risks $600 — close enough band. Do not upsize SIL to 3 contracts without an explicit override.

---

## Session Workflow

### Pre-window (20:45–20:59 ET)

1. Confirm chart is on **MGC**, 1m (and separately, **SIL**, 1m).
2. Confirm the LuxAlgo *Market Structure CHoCH/BOS (Fractal)* indicator is visible on both.
3. Note the prevailing structure into the window (last confirmed fractal highs/lows, prior BOS/CHoCH labels). This is orientation — it does not gate the trade.
4. Flat going in. No positions carried from earlier sessions.

### In-window (21:00–21:59 ET)

Per instrument (MGC and SIL independently):

1. Watch for the **first** qualifying structure event (CHoCH or BOS) stamped ≥ 21:00:00.
2. When a second same-direction event prints, verify:
   - Both events inside the window.
   - Same direction.
   - Both confirmed (not still-forming fractals).
3. Enter at/after the confirming bar close — 3 contracts for MGC, 2 contracts for SIL.
4. Place SL at the indicator's corresponding dashed line.
5. Place TP at 2R from entry.
6. Only **one** trade per instrument per session. First valid setup is the trade.

### Post-entry

- Trade runs to TP or SL. No manual management, no partials, no break-even moves.
- **[NEEDS CONFIRMATION]** If neither TP nor SL is hit by the close of the 22:00 bar, does the trade run to completion or force-exit at 22:00? Assumption: **trade runs to TP/SL past 22:00** (2R targets on 1m metals can still need more than the remaining window when the setup triggers late). Confirm and update this line with empirical data.

### End of session

- Log the trade(s): instrument, setup type (CHoCH→BOS or BOS→BOS), direction, entry/SL/TP prices, SL distance in points, time of each structure event, outcome.
- If no valid setup printed in the window for a given instrument, skip — no forcing trades outside the rules.

---

## TV MCP Tool Workflow

Mapping of the above to the TradingView MCP tools in this repo.

### Pre-window setup (per instrument)

```
chart_set_symbol        → "COMEX:MGC1!" or "COMEX_MINI:SIL1!"
chart_set_timeframe     → "1"
chart_get_state         → verify LuxAlgo "Market Structure CHoCH/BOS (Fractal)" is loaded
```

If the indicator isn't loaded:

```
chart_manage_indicator  → add "Market Structure CHoCH/BOS (Fractal) [LuxAlgo]"
```

### Reading structure events during the window

The LuxAlgo script draws its CHoCH/BOS labels and solid/dashed lines via Pine `label.new()` and `line.new()` — so they're only accessible through the Pine graphics tools:

```
data_get_pine_labels    study_filter="Market Structure"   → text labels ("CHoCH", "BOS") + prices + timestamps
data_get_pine_lines     study_filter="Market Structure"   → all lines currently drawn (solid + dashed)
data_get_structure_zones study_filter="Market Structure"  → compact events w/ direction + paired pivots
```

### Current price / quote

```
quote_get               → latest MGC/SIL price for entry confirmation
```

### Screenshot for log

```
capture_screenshot      region="chart"   → post-entry and post-exit snapshots
```

### Backtesting via replay

```
replay_start            date="YYYY-MM-DD"   → jump to a historical session
chart_scroll_to_date    date="YYYY-MM-DDT20:55:00"
replay_step / replay_autoplay  → walk the 21–22 window bar by bar
data_get_pine_labels    study_filter="Market Structure"   → record each break as it prints
```

---

## Invalidations & No-Trade Conditions

Skip the session entirely when any of these are true:

| Condition | Why |
|---|---|
| Chart is not MGC or SIL on 1m | Strategy is instrument- and timeframe-specific. |
| LuxAlgo MS Fractal is not visible | No signal source. |
| First qualifying event stamped before 21:00:00 | Outside the window — does not count. |
| Second event stamped after 21:59:59 | Outside the window — does not count. |
| The two events are opposite direction | Mixed sequence, not a setup. |
| Second event is still an unconfirmed fractal | No trade until the indicator prints the label. |
| A valid setup already triggered earlier in the window (for that instrument) | One trade per instrument per session. |
| Scheduled China macro release at 21:00 ET (NBS data, PBOC announcements) | Structure is meaningless across a release print. Skip. |

---

## Open Design Decisions

Explicitly unresolved — to be answered as we trade the strategy and observe behavior.

1. **Hard 22:00 exit?** — Does a trade in progress at 22:00 force-close, or run to TP/SL? (Current assumption: runs to completion.)
2. **MGC–SIL correlation gate** — Metals often move together. If MGC fires bullish at 21:08 and SIL fires bearish at 21:14, is that a valid divergence or noise to ignore? Currently both are taken independently. Data may show one direction dominates and the contrarian signal underperforms.
3. **Contextual filters** — Prior-session HTF bias, PDH/PDL proximity, Midnight Open, DXY direction, session VWAP. None applied yet. DXY is especially relevant for metals — a trending dollar during the window may gate trades.
4. **Event spacing** — Is there a minimum number of bars required between the two structure events? (Currently no.)
5. **Minimum SL distance** — Tight structural stops may produce degenerate R:R where slippage dominates. Minimum point floor? (Currently none.)
6. **CHoCH→BOS vs BOS→BOS — equal weight?** — Both valid today. Data may show one edge is materially stronger, particularly for post-sweep reversals common in overnight metals.
7. **Per-instrument sizing refinement** — Current default is MGC 3c / SIL 2c. Dollar risk still isn't perfectly matched and depends on SL distance of the session. Candidate rule: scale SIL dynamically based on the session's actual SL so dollar risk is always ±20% of MGC's.

---

## Empirical Behavior

> **Placeholder.** This section is intentionally empty until we run a dedicated replay study on MGC and SIL 1m across a statistically meaningful sample of sessions (target: ≥ 20 sessions per instrument, mixed market conditions).

Metrics to collect per session, per instrument:

- Did any setup print in the window? (Yes / No, type)
- Direction, entry price, SL price, TP price
- SL distance (points and dollars)
- Time-to-resolution and outcome (TP / SL / Unresolved at 22:00)
- Structural context at entry (trend vs counter-trend of prior session)
- Sequence type (CHoCH→BOS vs BOS→BOS)

Aggregate metrics to report:

- Setup frequency (% of sessions with ≥ 1 valid setup)
- Win rate — overall and split by sequence type, direction, and instrument
- Expectancy per session in R and in dollars
- Distribution of SL distance (for position-sizing sanity)
- Typical time-to-TP and time-to-SL
- Performance by approximate session type (trend night, range night, China-news night)
- MGC–SIL co-trade behavior (both fire same direction vs divergence)

Run via `replay_start` → walk 20:55 → 22:05 each day → log every CHoCH/BOS print via `data_get_pine_labels`, per instrument.

---

## Rules — Canonical Summary

1. MGC and SIL only. 1m only.
2. Window is 21:00–21:59 ET. Both structure events must print inside.
3. Valid setups: CHoCH → BOS or BOS → BOS, same direction, both confirmed.
4. Entry at/after the second event's bar close.
5. SL at the indicator's dashed line.
6. TP at 2R.
7. MGC 3 contracts · SIL 2 contracts (default sizing for dollar-risk parity).
8. One trade per instrument per session. First valid setup is the trade.
9. Skip the session on scheduled 21:00 ET China macro releases.
10. If in doubt, no trade.
