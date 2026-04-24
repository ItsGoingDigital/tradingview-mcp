---
name: silver-bullet
description: Silver Bullet strategy — MNQ only, 1m, 10–11 AM ET window. Identify two same-direction LuxAlgo Market Structure (Fractal) CHoCH/BOS events to take a 2R trade with 3 contracts. Use when the user asks for a silver-bullet setup, AM kill-zone trade on MNQ, or references the 10–11 ET window. Standalone — not part of ICC or S&D.
---

# Silver Bullet — MNQ AM Window

Produce one trade candidate (or a clean "no setup") for MNQ inside 10:00–11:00 AM ET. Background on the ICT AM Silver Bullet principle — why the window, why the indicator, empirical notes — lives in [REFERENCE.md](REFERENCE.md). REFERENCE is reading material, not an override: when this skill and REFERENCE differ, this skill wins.

## Prerequisites

Chart must have:
- Symbol `MNQ1!` (or `CME_MINI:MNQ1!`) on the **1m** timeframe.
- `Market Structure CHoCH/BOS (Fractal) [LuxAlgo]` — **period = 3** each side (not the default 5).

If the indicator is missing or mis-configured on `chart_get_state`, stop and tell the user — don't guess.

## Window

Hard bounds: **10:00:00 ≤ event time ≤ 10:59:59 ET**. Events outside this window do not count, even by one minute. If the current time is outside the window, say so — don't fabricate a setup.

## Setup rules

Take the **first** valid setup inside the window, then stand down (one trade per session).

A valid setup is **two consecutive same-direction confirmed structure events**, both stamped inside 10–11 ET. Valid sequences:

- **CHoCH → BOS** (reversal into continuation)
- **BOS → BOS** (pure continuation)

Entry = the **close** of the break-confirmation bar (not the fractal bar). Labels print at the break bar.

## Stop & target

- **SL** = the indicator's corresponding dashed line (paired opposing fractal). Structural, not fixed ticks.
- **TP** = entry ± 2 × (entry − SL). Fixed 2R.
- **Size** = 3 contracts.

## Workflow

1. `chart_set_symbol MNQ1!` · `chart_set_timeframe 1` (verify, don't assume).
2. `chart_get_state` → confirm indicator name and period.
3. `data_get_structure_zones` with `study_filter: "Market Structure"` → pull recent CHoCH/BOS events.
4. Filter events to those stamped **10:00–10:59 ET today**.
5. Look for the first valid 2-event sequence (CHoCH→BOS or BOS→BOS, same direction).
6. **Context cross-check (MANDATORY — see section below).** The mechanical pair is not enough.
7. If trigger passes cross-check: report entry / SL / TP / R-distance in points and grade. If trigger fails cross-check: report as Grade D · pass and explain why. If no valid pair at all: state which events (if any) landed inside the window.

## Context cross-check (MANDATORY before reporting a trigger)

The mechanical pair rules will fire on any same-direction CHoCH/BOS combination inside the window. That alone is not enough — a pair that triggers into an opposing S&D zone is a stop-out factory. A Silver Bullet trigger must pass this three-part check before it is reported as tradeable.

Run this the moment the 2nd same-direction event confirms, before posting the setup:

1. **Pull 15m S&D zones.** Temporarily `chart_set_timeframe 15`, call `data_get_structure_zones` (`within_points: 50`), then `chart_set_timeframe 1` to restore. (Per `feedback_pane_swap_permission.md` in memory, you have blanket permission to swap and restore.)
2. **Entry-inside-opposing-zone test.** For the proposed entry:
   - **Short setup:** if entry price falls inside the range of an unmitigated 15m **demand** zone (`sl ≤ entry ≤ entry_edge`), the trade is shorting into an active structural floor. **Grade D · pass.**
   - **Long setup:** mirror — if entry falls inside an unmitigated 15m **supply** zone, shorting into ceiling. **Grade D · pass.**
3. **4h trend alignment test.** Briefly pull 4h structure (`chart_set_timeframe 240` → `data_get_structure_zones include_mitigated: true` → `chart_set_timeframe 1`). Use the sequence of the last ~6 events to classify the 4h as Up / Down / Consolidating.
   - Pair aligned with 4h trend **and** entry zone clear → A/B eligible.
   - Pair counter to 4h trend **and** entry zone clear → Grade C (known risk, reduced size).
   - Pair counter to 4h trend **and** entry inside opposing zone → Grade D · pass. Do not take the trade.

**This check is non-negotiable.** The ChoCH/BOS indicator is a pattern detector, not a context engine. Zones are the context. Skipping this check has cost real trades — see `feedback_silver_bullet_zone_check.md` in memory for the 2026-04-24 incident where a mechanically valid bearish pair at 10:11 fired straight into 15m demand 27169.50–27194.00, got 9 pts of MFE, and stopped out for −1R seven minutes later.

## Setup Grades

- **A** — Clean CHoCH→BOS or BOS→BOS inside window; SL dashed line sits at a structural low/high with comfortable cushion (≥15 pts); TP projects into open air or a known liquidity magnet; setup prints in the first 30 minutes of the window. Take **full 3 contracts**.
- **B** — Valid setup, one weakness: SL cushion is tight (<15 pts), or TP lands inside visible congestion, or the pattern fires in the back half of the window. Standard 3 contracts; manage actively.
- **C** — Valid pattern but a known friction: triggers in last 15 min of window (short runway to TP), coincides with scheduled economic release, or is the first event after a failed prior setup nearby. Reduce to 1–2 contracts or shorten the hold.
- **D** — Structural pattern is valid but the context cross-check fails: entry falls inside an opposing 15m S&D zone, the pair fights a stacked 4h wall, or a major liquidity pool sits directly between entry and TP. **Watch only — do not take the trade.**
- **F** — No valid setup — fewer than two same-direction events in window, direction mixed, or indicator silent.

---

## Output template (single-block Playbook style)

```
# Silver Bullet — MNQ {YYYY-MM-DD}

**10–11 AM ET Window · 1m · LuxAlgo MS Fractal (period 3)**

{One-line headline: the shape of the window. e.g., "Two bullish BOS early, clean 2R by 10:40." Or: "No setup — direction never resolved." }

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
| 1 | 10:HH | {CHoCH|BOS} | 🟢/🔴 | {price} | {H|L} {price} | {fractal timestamp, if useful} |
| 2 | 10:HH | {CHoCH|BOS} | 🟢/🔴 | {price} | {H|L} {price} | **← trigger (2nd same-dir event)** |
| ... | | | | | | |

If fewer than 2 same-direction events printed in window, list what printed and say "no valid pair."

---

## The Setup

> **{Long | Short} @ {entry} · SL {sl} · TP {tp}**
> **Risk {R} pts · Reward {2R} pts · 2R · 3 contracts**

**Grade rationale:** {one or two sentences on why this grade — cite SL cushion, TP runway, window timing, context friction, etc.}

---

## Context cross-check

**Mandatory for every trigger.** Populate all three lines — blank means the check was skipped, which invalidates the grade.

- **15m S&D at entry:** {e.g., "entry 27175.75 **inside 15m demand 27169.50–27194** → FAIL" | "entry 27310.25 in fresh air → PASS" | "entry 27285 inside 15m supply (same-dir confluence) → BONUS"}
- **4h trend:** {Up | Down | Consolidating} — {aligned | counter} to the pair direction
- **Verdict:** {PASS · A/B/C eligible | SKIP · Grade D}

## Liquidity & Context

- **Above:** {PDH, PWH, Midnight Open, Day Open, etc., with absolute prices and distance in pts — e.g., "PDH 27,040 (+37)" }
- **Below:** {PDL, PWL, Day Open, etc.}
- **HTF wall (if relevant):** {e.g., "4h supply 27,100–27,180 sits 100 pts above TP — no threat" or "15m demand 26,860–26,880 overlaps SL line — reinforces stop"}

If you can't pull these confidently, note "no context layers checked" — do not fabricate.

---

## The Trade

- **Entry:** {price} — close of {HH:MM} break-confirmation bar
- **Stop:** {price} — LuxAlgo dashed line paired to the {BOS | CHoCH} (opposing confirmed fractal at {HH:MM})
- **Target:** {price} — entry {+|-} 2 × {R} pts

### P&L at target (2R, {2R} pts)

| Contracts | Risk | Reward |
|---:|---:|---:|
| 3 | −${risk×2×3} | **+${2R×2×3}** |
| 5 | −${risk×2×5} | **+${2R×2×5}** |
| 10 | −${risk×2×10} | **+${2R×2×10}** |

MNQ = $2.00 / pt / contract.

### The Read

{One paragraph — 3–5 sentences. What did institutional flow say, how clean is the SL anchor, does TP align with a real magnet, what are the live risks, what would invalidate the thesis before TP? Plain language, no jargon for jargon's sake.}

---

## Outcome {include only after TP / SL hit or 11:00 window close}

- **{HH:MM}:** {key milestone — e.g., "MFE of {pts} pts at {price}" / "deepest pullback to {price}, {pts} pts above SL"}
- **{HH:MM}:** {TP fill | SL stop | still open at 11:00}
- **Time in trade:** {N} minutes
- **Result:** {+2R | −1R | unresolved at window close — see decision log}
- **P&L:** 3c = **${X}** · 5c = **${Y}** · 10c = **${Z}**

---

## Bottom Line

{One or two sentences. The honest takeaway — was this a textbook win, a grind, a stop-out, a pass? What does it say about the morning's tape? One-line discipline reminder if relevant.}
```

### When the setup never fires

Keep the same top header, the Status line ("🔴 No setup · window closed"), the Events in Window table (showing whatever printed), and a **Bottom Line** that explains why in one sentence (e.g., "Direction flipped four times inside the window — no consecutive same-direction pair"). Skip The Setup / Liquidity / The Trade / Outcome sections entirely. Do not fabricate a grade.

### When we're mid-window

Headline says "waiting" or reports the current partial structure. Status is 🟡. Fill Events in Window with whatever's printed. Skip The Setup section until the second same-direction event confirms, then promote.

## Rules (no exceptions)

1. MNQ only — never apply this to MES, ES, NQ, or any other symbol.
2. Both events must be inside 10:00–10:59 ET. A break at 09:59 or 11:00 disqualifies it.
3. Same direction — a bullish CHoCH paired with a bearish BOS is not a setup.
4. One trade per session. First valid setup takes it.
5. Fixed 2R. Do not widen TP mid-trade.
6. Vocabulary is pure structure (CHoCH, BOS, fractal, entry, SL, TP). Do not import ICC/PD Array language. S&D zones are the one exception — they're used **only** for the context cross-check, not for narrative.
7. **MANDATORY context cross-check.** Every trigger must be cross-checked against 15m S&D zones and 4h trend before being reported as tradeable. Entry inside an opposing 15m zone → Grade D · pass. Counter to 4h trend AND inside opposing zone → Grade D · pass. The mechanical pair rules produce a pattern; the context check decides if it is tradeable. A report missing the "Context cross-check" section in the output is incomplete.
