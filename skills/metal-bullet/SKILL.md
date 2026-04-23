---
name: metal-bullet
description: Metal Bullet strategy — MGC and SIL only, 1m, 21:00–22:00 ET window. Identify two same-direction LuxAlgo Market Structure (Fractal) CHoCH/BOS events to take a 2R trade with 3 contracts. Use when the user asks for a metal-bullet setup, Shanghai AM kill-zone trade on MGC or SIL, or references the 21–22 ET window. Standalone — not part of ICC, S&D, or Silver Bullet.
---

# Metal Bullet — MGC / SIL Shanghai AM Window

Produce one trade candidate (or a clean "no setup") for MGC **and** one for SIL inside 21:00–22:00 ET. Background on the Shanghai AM principle — why the window, why metals, empirical notes — lives in [REFERENCE.md](REFERENCE.md). REFERENCE is reading material, not an override: when this skill and REFERENCE differ, this skill wins.

## Prerequisites

Chart must have:
- Symbol `MGC1!` (or `COMEX:MGC1!`) and `SIL1!` (or `COMEX_MINI:SIL1!`) — analyze each separately on the **1m** timeframe.
- `Market Structure CHoCH/BOS (Fractal) [LuxAlgo]` — **period = 3** each side (not the default 5).

If the indicator is missing or mis-configured on `chart_get_state`, stop and tell the user — don't guess.

## Window

Hard bounds: **21:00:00 ≤ event time ≤ 21:59:59 ET**. Events outside this window do not count, even by one minute. If the current time is outside the window, say so — don't fabricate a setup.

## Setup rules

Take the **first** valid setup inside the window **per instrument**, then stand down (one trade per instrument per session). Up to **two trades total** in the window — one MGC, one SIL — if both print valid setups independently.

A valid setup is **two consecutive same-direction confirmed structure events**, both stamped inside 21–22 ET. Valid sequences:

- **CHoCH → BOS** (reversal into continuation)
- **BOS → BOS** (pure continuation)

Entry = the **close** of the break-confirmation bar (not the fractal bar). Labels print at the break bar.

## Stop & target

- **SL** = the indicator's corresponding dashed line (paired opposing fractal). Structural, not fixed ticks.
- **TP** = entry ± 2 × (entry − SL). Fixed 2R.
- **Size:** MGC = 3 contracts · SIL = **2 contracts** (sized down for dollar-risk parity).

## Contract values

- **MGC** (Micro Gold): **$10 / pt / contract** (10 troy oz, tick 0.10 = $1).
- **SIL** (Micro Silver): **$1,000 / pt / contract** (1,000 troy oz, tick 0.005 = $5). A 0.01 move = $10 per contract.

SIL's per-point dollar exposure is ~100× MGC's, so SIL size is **2 contracts** (not 3) to keep dollar risk in a comparable band. Rough sanity check: 3 MGC × 15 pt SL = $450 risk; 2 SIL × 0.30 pt SL = $600 risk. Close enough. Do not upsize SIL to 3 without explicit user override.

## Workflow

1. `chart_set_symbol MGC1!` · `chart_set_timeframe 1` (verify, don't assume).
2. `chart_get_state` → confirm indicator name and period.
3. `data_get_structure_zones` with `study_filter: "Market Structure"` → pull recent CHoCH/BOS events.
4. Filter events to those stamped **21:00–21:59 ET today**.
5. Look for the first valid 2-event sequence (CHoCH→BOS or BOS→BOS, same direction).
6. If found: report entry / SL / TP / R-distance in points. If not: say so and state which (if any) events landed inside the window.
7. Repeat steps 1–6 for `SIL1!`.

## Setup Grades

- **A** — Clean CHoCH→BOS or BOS→BOS inside window; SL dashed line sits at a structural low/high with comfortable cushion (MGC ≥10 pts, SIL ≥0.20); TP projects into open air or a known liquidity magnet; setup prints in the first 30 minutes of the window. Take **full 3 contracts**.
- **B** — Valid setup, one weakness: SL cushion is tight, or TP lands inside visible congestion, or the pattern fires in the back half of the window. Standard 3 contracts; manage actively.
- **C** — Valid pattern but a known friction: triggers in last 15 min of window (short runway to TP), coincides with scheduled macro news, or is the first event after a failed prior setup nearby. Reduce to 1–2 contracts or shorten the hold.
- **D** — Structural pattern is valid but the setup fights an obvious higher-context wall (stacked HTF resistance/support, major liquidity pool directly between entry and TP). Watch only.
- **F** — No valid setup — fewer than two same-direction events in window, direction mixed, or indicator silent.

---

## Output template (single-block Playbook style)

Each session produces **one analysis file per instrument**: `YYYY-MM-DD-MGC-MB.md` and/or `YYYY-MM-DD-SIL-MB.md`. If only one instrument prints a setup, only that file is written; the other can be noted in a one-line status or skipped.

```
# Metal Bullet — {SYMBOL} {YYYY-MM-DD}

**21–22 PM ET Window · 1m · LuxAlgo MS Fractal (period 3)**

{One-line headline: the shape of the window. e.g., "Two bullish BOS by 21:15, clean 2R by 21:42." Or: "No setup — direction never resolved." }

---

## Status

{🟢 Setup found · trade {live | TP hit | SL hit} | 🟡 Waiting · window in progress | 🔴 No setup · window closed}

---

## The Board

| | |
|---|---|
| Pattern | {CHoCH→BOS | BOS→BOS} {bull | bear} |
| Grade | {A | B | C | D | F} |
| Entry | {price} |
| Stop | {price} |
| Target | {price} ({2R} pts) |
| Risk | {R} pts |
| Result | {✅ +2R | ❌ −1R | ⏳ Open | — } |

---

## Events in Window

Use these columns every time — blank out fields when unknown.

| # | Time (ET) | Event | Dir | Broken level | Bar H/L | Notes |
|---|---|---|---|---:|---:|---|
| 1 | 21:HH | {CHoCH|BOS} | 🟢/🔴 | {price} | {H|L} {price} | {fractal timestamp, if useful} |
| 2 | 21:HH | {CHoCH|BOS} | 🟢/🔴 | {price} | {H|L} {price} | **← trigger (2nd same-dir event)** |
| ... | | | | | | |

If fewer than 2 same-direction events printed in window, list what printed and say "no valid pair."

---

## The Setup

> **{Long | Short} @ {entry} · SL {sl} · TP {tp}**
> **Risk {R} pts · Reward {2R} pts · 2R · {3 contracts (MGC) | 2 contracts (SIL)}**

**Grade rationale:** {one or two sentences on why this grade — cite SL cushion, TP runway, window timing, context friction, etc.}

---

## Liquidity & Context

- **Above:** {PDH, PWH, Midnight Open, Day Open, etc., with absolute prices and distance in pts}
- **Below:** {PDL, PWL, Day Open, etc.}
- **HTF wall (if relevant):** {e.g., "4h supply 4820–4854 sits 50 pts above TP — no threat" or "15m demand 77.45–77.70 overlaps SL line — reinforces stop"}

If you can't pull these confidently, note "no context layers checked" — do not fabricate.

---

## The Trade

- **Entry:** {price} — close of {HH:MM} break-confirmation bar
- **Stop:** {price} — LuxAlgo dashed line paired to the {BOS | CHoCH} (opposing confirmed fractal at {HH:MM})
- **Target:** {price} — entry {+|-} 2 × {R} pts

### P&L at target (2R, {2R} pts)

**MGC** ($10 / pt / contract · default 3 contracts):

| Contracts | Risk | Reward |
|---:|---:|---:|
| 3 | −${risk × 10 × 3} | **+${2R × 10 × 3}** |
| 5 | −${risk × 10 × 5} | **+${2R × 10 × 5}** |
| 10 | −${risk × 10 × 10} | **+${2R × 10 × 10}** |

**SIL** ($1,000 / pt / contract · default 2 contracts):

| Contracts | Risk | Reward |
|---:|---:|---:|
| 2 | −${risk × 1000 × 2} | **+${2R × 1000 × 2}** |
| 3 | −${risk × 1000 × 3} | **+${2R × 1000 × 3}** |
| 5 | −${risk × 1000 × 5} | **+${2R × 1000 × 5}** |

Include only the table matching the instrument this file is for.

### The Read

{One paragraph — 3–5 sentences. What did institutional flow say, how clean is the SL anchor, does TP align with a real magnet, what are the live risks, what would invalidate the thesis before TP? Plain language, no jargon for jargon's sake.}

---

## Outcome {include only after TP / SL hit or 22:00 window close}

- **{HH:MM}:** {key milestone — e.g., "MFE of {pts} pts at {price}" / "deepest pullback to {price}, {pts} pts above SL"}
- **{HH:MM}:** {TP fill | SL stop | still open at 22:00}
- **Time in trade:** {N} minutes
- **Result:** {+2R | −1R | unresolved at window close — see decision log}
- **P&L:** 3c = **${X}** · 5c = **${Y}** · 10c = **${Z}**

---

## Bottom Line

{One or two sentences. The honest takeaway — was this a textbook win, a grind, a stop-out, a pass? What does it say about the overnight tape? One-line discipline reminder if relevant.}
```

### When the setup never fires

Keep the same top header, the Status line ("🔴 No setup · window closed"), the Events in Window table (showing whatever printed), and a **Bottom Line** that explains why in one sentence (e.g., "Direction flipped three times inside the window — no consecutive same-direction pair"). Skip The Setup / Liquidity / The Trade / Outcome sections entirely. Do not fabricate a grade.

### When we're mid-window

Headline says "waiting" or reports the current partial structure. Status is 🟡. Fill Events in Window with whatever's printed. Skip The Setup section until the second same-direction event confirms, then promote.

## Rules (no exceptions)

1. MGC and SIL only — never apply this to MNQ, MES, ES, NQ, or any other symbol.
2. Both events must be inside 21:00–21:59 ET. A break at 20:59 or 22:00 disqualifies it.
3. Same direction — a bullish CHoCH paired with a bearish BOS is not a setup.
4. One trade per instrument per session. First valid setup takes it.
5. Fixed 2R. Do not widen TP mid-trade.
6. Do not import vocabulary from ICC, S&D, PD Array, or Silver Bullet here. This is pure structure.
