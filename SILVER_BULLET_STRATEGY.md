# Silver Bullet Strategy — MNQ 10–11 AM ET

**ICT Silver Bullet window. 1-minute execution. Structure-confirmed entries via LuxAlgo Market Structure Fractal.**

---

## Scope

This is a standalone intraday strategy. It is **not** part of ICC and does not compose with it. Do not apply it to MES, ES, NQ, or any other instrument — MNQ only.

| Parameter | Value |
|---|---|
| Instrument | MNQ (Micro E-mini Nasdaq 100) |
| Session window | **10:00–11:00 AM ET** (hard bounds) |
| Execution timeframe | 1 minute |
| Indicator | LuxAlgo — *Market Structure CHoCH/BOS (Fractal)*, **period = 3 bars each side** |
| Position size | **3 contracts** |
| Risk:Reward | Fixed **2R** (2:1) |

The 10–11 AM ET window is the ICT "AM Silver Bullet" — a one-hour execution kill-zone that sits between the 9:30 NY open drive and the lunch lull. The edge thesis: by 10:00, the opening range has resolved, early liquidity has been taken, and the session's directional move often prints its cleanest structural leg inside this hour.

---

## The Indicator

**LuxAlgo — Market Structure CHoCH/BOS (Fractal)** plots swing fractals and labels every fractal break as one of two events:

- **BOS (Break of Structure)** — price breaks a fractal in the direction of the prevailing structure. Continuation signal.
- **CHoCH (Change of Character)** — price breaks a fractal *against* the prevailing structure. First sign of a potential reversal. A CHoCH is always the first counter-trend break; subsequent same-direction breaks are BOS.

**Indicator settings — critical:** Run the indicator with **period = 3 bars on each side** (a 7-bar fractal), not the default 5. Institutional moves during the 10–11 window are fast and often trend continuously — at 5-each-side, would-be fractals get invalidated by the next higher high / lower low before they're confirmed, and the indicator silently skips structural breaks that are happening in real time. 3-each-side is fast enough to keep up with the window's pace without being so loose that noise fires labels.

**Label timing — critical:** A BOS or CHoCh label **only appears at the moment of break confirmation**. The label stamps the **break bar**, not the fractal bar — i.e., the label's time is when price actually took out the prior swing, not when the swing itself formed. This is the bar we use for setup timing and entry.

**Line conventions on the indicator:**

- **Solid line** — drawn at the broken fractal level (the level price just took out). This is the *event* price.
- **Dashed line** — drawn at the opposite confirmed fractal that formed since the break. This is the structural invalidation reference — the level that, if broken, would invalidate the new direction.

The dashed line is what we use as the **stop loss**.

---

## The Setup

An entry requires **two consecutive same-direction structure events**, both printed by the indicator **inside the 10–11 window**. Exactly two valid sequences:

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
- Stamped inside the window — the timestamp of each break must fall between 10:00:00 and 10:59:59 ET.

Mixed sequences are **not** valid setups:
- BOS → CHoCH (opposite direction by definition) — no.
- CHoCH → CHoCH in the same direction — cannot happen; the second break is a BOS by indicator logic.
- CHoCH → CHoCH in opposite directions — whipsaw, no trade.

---

## Entry, Stop, Target

| Component | Rule |
|---|---|
| **Entry** | Market entry at/after the bar close that prints the second (confirming) structure event. |
| **Stop loss** | The **dashed line** the indicator shows corresponding to the triggering structure event — i.e., the opposing confirmed fractal. For a long: the dashed low below price. For a short: the dashed high above price. Do not use a fixed tick offset. |
| **Take profit** | **2R** — distance from entry to stop, multiplied by 2, projected in the trade direction. |
| **Size** | 3 MNQ contracts. |

Stops and targets are both structural-to-fixed: SL is anchored to indicator structure, TP is a fixed multiple of that structural risk.

---

## Session Workflow

### Pre-window (09:45–09:59 ET)

1. Confirm chart is on **MNQ, 1m**.
2. Confirm the LuxAlgo *Market Structure CHoCH/BOS (Fractal)* indicator is visible.
3. Note the prevailing structure into the window (last confirmed fractal highs/lows, prior BOS/CHoCH labels). This is orientation — it does not gate the trade.
4. Flat going in. No positions carried from earlier sessions.

### In-window (10:00–10:59 ET)

1. Watch for the **first** qualifying structure event (CHoCH or BOS) stamped ≥ 10:00:00.
2. When a second same-direction event prints, verify:
   - Both events inside the window.
   - Same direction.
   - Both confirmed (not still-forming fractals).
3. Enter 3 contracts at/after the confirming bar close.
4. Place SL at the indicator's corresponding dashed line.
5. Place TP at 2R from entry.
6. Only **one** trade per session. First valid setup is the trade.

### Post-entry

- Trade runs to TP or SL. No manual management, no partials, no break-even moves.
- **[NEEDS CONFIRMATION]** If neither TP nor SL is hit by the close of the 11:00 bar, does the trade run to completion or force-exit at 11:00? Assumption in this doc: **trade runs to TP/SL past 11:00** (2R targets on 1m MNQ can still need more than the remaining window when the setup triggers late). Confirm and update this line.

### End of session

- Log the trade: setup type (CHoCH→BOS or BOS→BOS), direction, entry/SL/TP prices, SL distance in points, time of each structure event, outcome.
- If no valid setup printed in the window, skip — no forcing trades outside the rules.

---

## TV MCP Tool Workflow

Mapping of the above to the TradingView MCP tools in this repo.

### Pre-window setup

```
chart_set_symbol        → "CME_MINI:MNQ1!"
chart_set_timeframe     → "1"
chart_get_state         → verify LuxAlgo "Market Structure CHoCH/BOS (Fractal)" is loaded
```

If the indicator isn't loaded:

```
chart_manage_indicator  → add "Market Structure CHoCH/BOS (Fractal) [LuxAlgo]"
```

### Reading structure events during the window

The LuxAlgo script draws its CHoCH/BOS labels and solid/dashed lines via Pine `label.new()` and `line.new()` — so they're only accessible through the Pine graphics tools, not `data_get_study_values`:

```
data_get_pine_labels    study_filter="Market Structure"   → text labels ("CHoCH", "BOS") + prices + timestamps
data_get_pine_lines     study_filter="Market Structure"   → all lines currently drawn (solid + dashed)
```

For the SL dashed line specifically, the line-style metadata is what distinguishes it — request with `verbose: true` once per entry if needed:

```
data_get_pine_lines     study_filter="Market Structure"   verbose=true
```

### Current price / quote

```
quote_get               → latest MNQ price for entry confirmation
```

### Screenshot for log

```
capture_screenshot      region="chart"   → post-entry and post-exit snapshots
```

### Backtesting via replay

```
replay_start            date="YYYY-MM-DD"   → jump to a historical session
chart_scroll_to_date    date="YYYY-MM-DDT09:55:00"
replay_step / replay_autoplay  → walk the 10–11 window bar by bar
data_get_pine_labels    study_filter="Market Structure"   → record each break as it prints
```

---

## Invalidations & No-Trade Conditions

Skip the session entirely when any of these are true:

| Condition | Why |
|---|---|
| Chart is not MNQ on 1m | Strategy is instrument- and timeframe-specific. |
| LuxAlgo MS Fractal is not visible | No signal source. |
| First qualifying event stamped before 10:00:00 | Outside the window — does not count. |
| Second event stamped after 10:59:59 | Outside the window — does not count. |
| The two events are opposite direction | Mixed sequence, not a setup. |
| Second event is still an unconfirmed fractal | No trade until the indicator prints the label. |
| A valid setup already triggered earlier in the window | One trade per session, period. |
| Major scheduled economic release at 10:00 ET | Structure is meaningless across the release print. Skip. |

---

## Open Design Decisions

Explicitly unresolved — to be answered as we trade the strategy and observe behavior.

1. **Hard 11:00 exit?** — Does a trade in progress at 11:00 force-close, or run to TP/SL? (Current assumption: runs to completion.)
2. **Contextual filters** — Prior-session HTF bias, PDH/PDL proximity, overnight high/low, NWOG, session VWAP, killzone confluence (ICT AM Session vs NY AM), etc. None applied yet. Any of these could be added as a gate once empirical data justifies it.
3. **Event spacing** — Is there a minimum number of bars required between the two structure events? (Currently no — back-to-back same-bar-to-next-bar is acceptable.)
4. **Minimum SL distance** — Very tight structural stops may produce degenerate R:R where slippage/commissions dominate. Minimum point floor? (Currently none.)
5. **CHoCH→BOS vs BOS→BOS — equal weight?** — Both are valid setups today. Data may show one edge is materially stronger.

---

## Empirical Behavior

> **Placeholder.** This section is intentionally empty until we run a dedicated replay study on MNQ 1m across a statistically meaningful sample of sessions (target: ≥ 20 sessions, mixed market conditions).

Metrics to collect per session:

- Did any setup print in the window? (Yes / No, type)
- Direction, entry price, SL price, TP price
- SL distance (points)
- Time-to-resolution and outcome (TP / SL / Unresolved at 11:00)
- Structural context at entry (trend vs counter-trend of prior session)
- Sequence type (CHoCH→BOS vs BOS→BOS)

Aggregate metrics to report:

- Setup frequency (% of sessions with ≥ 1 valid setup)
- Win rate — overall and split by sequence type and direction
- Expectancy per session in R
- Distribution of SL distance (for position-sizing sanity)
- Typical time-to-TP and time-to-SL
- Performance by approximate session type (trend day, range day, news day)

Run via `replay_start` → walk 09:55 → 11:05 each day → log every CHoCH/BOS print via `data_get_pine_labels`.

---

## Rules — Canonical Summary

1. MNQ only. 1m only.
2. Window is 10:00–10:59 ET. Both structure events must print inside.
3. Valid setups: CHoCH → BOS or BOS → BOS, same direction, both confirmed.
4. Entry at/after the second event's bar close.
5. SL at the indicator's dashed line.
6. TP at 2R.
7. 3 contracts.
8. One trade per session. First valid setup is the trade.
9. Skip the session on scheduled 10:00 ET economic releases.
10. If in doubt, no trade.
