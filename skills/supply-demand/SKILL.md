---
name: supply-demand
description: Analyze supply and demand zones on futures charts using Lux Algo Market Structure (Fractal) ChoCh/BoS events. Multi-symbol, multi-timeframe, grounded in basic market structure (HH/HL/LH/LL) and zones only — no ICC, PD Array, ICT, or other strategy vocabulary. Use when the user asks for S&D analysis, zones, entries, or "what's my setup" on MNQ/MES/SIL/MGC (or any user-specified symbol list).
---

# Supply & Demand Analysis

Produce a clean, decision-ready report per symbol using only **basic market structure** and **S&D zones**. Do not pull from other strategies (ICC, PD Array, ICT, Silver Bullet, etc.) — strict separation.

Background on the principle itself — zone types, drawing theory, why flip zones flip, multi-timeframe rationale — lives in [REFERENCE.md](REFERENCE.md). REFERENCE is reading material, not an override: when this skill and REFERENCE differ, this skill wins.

## Vocabulary (stay inside this set)

- **Market structure:** HH, HL, LH, LL. Trend = Up / Down / Consolidating.
- **Zone:** one rectangle from a Lux Algo Market Structure (Fractal) ChoCh/BoS event.
  - Bullish ChoCh/BoS → **demand zone** (long setup)
  - Bearish ChoCh/BoS → **supply zone** (short setup)
- **Zone edges:**
  - **Entry** = solid line = the broken structural level (ChoCh/BoS label price).
  - **SL** = dashed line = the paired pivot on the opposite side of the impulse.
- **Unmitigated** = price has not *closed* (wick excluded) through the SL edge. The indicator leaves the dashed line open when unmitigated.
- **FVG** = confluence only; never the thesis.

## Prerequisites

The chart must have these indicators visible:
- `Market Structure CHoCH/BOS (Fractal) [LuxAlgo]`
- `FVG/iFVG (Nephew_Sam_)` (one or more instances, typically tuned per TF)

If either is missing on `chart_get_state`, stop and tell the user — don't guess at indicator names to add.

## Default symbols & timeframes

- Symbols (unless user overrides): `MNQ1!`, `MES1!`, `SIL1!`, `MGC1!`. Use full CME/COMEX prefixes if plain symbols fail (`CME_MINI:MNQ1!`, `COMEX:MGC1!`).
- Timeframes: **4h** then **15m** (pair).
- Fallback pair: **1h** + **5m** — ask the user before switching.

## Session notes (MGC, SIL)

Metals zones can be delivered overnight — overnight is not "thin." Tradeable windows (avg hourly range ≈ RTH): **21:00 ET** (Shanghai AM) and **07:00–09:00 ET** (Europe / US pre-open). Dead zones to skip: **23:00–01:00 ET** and **04:00–06:00 ET**.

## Workflow

### 1. Per symbol, per timeframe

1. `chart_set_symbol`
2. `chart_set_timeframe` (240 for 4h, 15 for 15m)
3. Brief wait for indicator recompute (the tool returns `chart_ready` but primitives may lag ~1s — acceptable).
4. `data_get_structure_zones` with `study_filter: "Market Structure"`, `within_points: 100` → returns all unmitigated zones within ±100 pts of current price, sorted nearest first. Each zone object: `{event, direction, zone_type, entry, sl, risk, tp_3R, size, bar_idx, mitigated}`.
5. `data_get_pine_boxes` with `study_filter: "FVG"` → returns live FVG zones as `{high, low}` arrays per FVG indicator instance.
6. `quote_get` (already folded into `data_get_structure_zones.current_price`, but call separately if you need OHLC or description).

### 2. Derive the trend per TF

Use the **sequence of the last ~6 BOS/ChoCh events** from `data_get_structure_zones` (pass `include_mitigated: true` for this step to see the recent history — then filter the analysis).

- **Up:** consecutive bullish BOS/ChoCh, making HH + HL.
- **Down:** consecutive bearish BOS/ChoCh, making LH + LL.
- **Consolidating:** alternating bullish/bearish within a tight range (no net new HH or LL).

If 4h and 15m both look consolidating, **stop and ask** the user: *"4h and 15m are consolidating — want me to analyze 1h and 5m instead?"*

### 3. Build entries

For each unmitigated zone returned by `data_get_structure_zones`, the tool has already computed:
- `entry` = solid line price
- `sl` = dashed line price
- `risk` = |entry − SL|
- `tp_3R` = entry ± 3×risk (+ for demand, − for supply)

Present entry/SL/TP **in points** (no dollar math). Note size (= risk in points) — smaller zones are preferred.

### 4. Check confluence

For each proposed entry, flag these (bullet per hit):
- **Cross-TF same-direction zone overlap:** a 4h demand zone overlaps a 15m demand zone if `[min(entry,sl), max(entry,sl)]` ranges intersect. Same for supply.
- **FVG overlap on same TF:** iterate the FVG `zones` array and flag if any FVG `[low, high]` intersects the S&D zone range.
- **Untouched FVG bonus:** Nephew_Sam auto-removes mitigated FVGs — so any FVG box still present on chart is a candidate. Flag it as "untouched FVG confluence" when it overlaps.

### 5. Closest zones section

Per TF: the **closest unmitigated demand below price** and the **closest unmitigated supply above price**. The tool's output is already sorted by distance from price — demand below is the nearest zone with `entry < current_price`, supply above is the nearest with `entry > current_price`. If there are none within 100 pts in a given direction, say so.

## Output template

**Deliverable.** Save each session as a standalone markdown file in `analysis/` using filename format `YYYY-MM-DD-HHMMET.md` (24-hour, timezone suffix, e.g. `2026-04-22-1326ET.md`). Multiple sessions per day are expected. The file is the finished product — written for a paying Discord subscriber, not an internal analyst.

**Canonical example:** see [`analysis/2026-04-22-1326ET.md`](../../analysis/2026-04-22-1326ET.md).

### Audience & voice

- **Audience:** hungry, eager-to-learn, eager-to-act traders paying premium for decisive counsel.
- **Voice:** informative, clear, decisive. Active voice. Short sentences. AP style.
- **Dates:** `April 22, 2026 · 1:26 p.m. ET` in prose. ISO in filenames.
- **Numbers:** numerals for all prices, points, sizes, grades.

### Grading rubric (A / B / C / D / F)

Letter grade on every setup. Reflects confluence quality; does not override the Call — it informs sizing.

- **A** — Every layer aligns: trend, cross-TF zone stack, tight size, liquidity magnet, fresh event. Take full size.
- **B** — Strong setup missing one confluence. Take standard size.
- **C** — Tradeable with a known risk (counter-trend, no cross-TF stack, wide zone). Reduce size or shorten hold.
- **D** — Valid structure, thesis has a gap (usually missing liquidity magnet). Watch only.
- **F** — Pass.

Use `+` or `-` modifiers for exceptional features (extreme tightness, 3R-lands-on-Midnight-Open geometry, etc.).

### Document structure (in order)

1. **Header** — `# Futures Playbook` + bold date/time + one-line vibe check.
2. **Setup Grades legend** — the A/B/C/D/F rubric verbatim.
3. **Top Call** — blockquote with top pick's Entry · Stop · Target, then 2–3 sentence thesis.
4. **The Board** — 7-col summary: Symbol · Grade · Call · Entry · Stop · Target · Risk. Top pick bolded in Symbol and Grade cells.
5. **Per-symbol sections** — identical structure across symbols (template below).
6. **Bottom Line** — decisive recap: one swing + grade, tacticals + grades, passes + grades. One-line risk reminder close.

### Per-symbol section (identical order every time)

```
## {TICKER} — {Description} · {price} · Grade {X}

**Trend:** 4h {Up/Down/Choppy} ({ICC phase}) · 15m {Up/Down/Choppy}
**Call:** **{GO LONG / GO SHORT / WATCH / PASS}** — {one-line verdict}
**Grade rationale:** {one line — what layers aligned or didn't}

### Zones

| TF  | Type           | Range       | Size    | Note                         |
|-----|----------------|-------------|---------|------------------------------|
| 15m | Demand/Supply  | low — high  | X pts   | fresh / stale / stacked / … |
| 4h  | Demand/Supply  | low — high  | X pts   | …                            |

Optional note below table: "Zones overlap at X — X" (cross-TF stack).

### Liquidity

- **Above (buy stops):** PDH X · PWH X · MO X · {cluster/taken flags}
- **Below (sell stops):** DO X · PDL X · Month Open X · {cluster flags}

### The Trade

- **Entry:** X — {zone reference}
- **Stop:** X — {invalidation}
- **Target:** X — {magnet reference, 3R}
- **Risk / Reward:** X pts / X pts
- **Runner target (optional):** X — {extended magnet}

### The Read

{2–3 sentences. Plain-English thesis: what price is doing, why the setup works, what kills it.}
```

### ICC phase (4h only)

Append the ICC phase to the 4h trend label in parentheses: `4h Up (Continuation)`. Do **not** add it to the 15m — it gets confusing. Phases: Indication · Correction · Continuation · No Trade (choppy). See [`docs/strategies/icc.md`](../../docs/strategies/icc.md) for definitions. Does not affect grading.

### Context budget

- Each symbol section: ~1,000–1,500 bytes. The newsletter is the deliverable, not raw telemetry.
- Never dump raw tool JSON. Summarize into the tables and prose above.
- No screenshots unless the user asks.
- If a symbol has no unmitigated zones within the search window in either direction, give it a one-line "No actionable setup" note and move on. Do not invent zones.

## Rules (no exceptions)

1. Only trade **unmitigated** zones (`mitigated: false`). Never propose entries off mitigated zones.
2. Entry = `sol` (solid / ChoCh/BoS label price). SL = `dsh` (dashed pivot). TP = entry ± 3×risk. These come directly from `data_get_structure_zones`.
3. Zones are rectangles — always quote both edges.
4. FVG is confluence only. A zone without FVG overlap is still tradable; an FVG without a zone is not.
5. If 4h/15m is unclear (both consolidating, or conflicting trends with no same-direction confluence), ask before falling back to 1h/5m.
6. Do not import vocabulary from other strategies. No "bias," "PD Array," "indication," "correction," etc.
7. Tighter zones beat wider zones — always note size in the report.
