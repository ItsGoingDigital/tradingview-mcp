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

One block per symbol. Keep it tight.

```
## {SYMBOL} — {price} ({description})

**Trend:** 4h {Up|Down|Consolidating} · 15m {Up|Down|Consolidating}

**Closest zones (unmitigated, within 100 pts):**
| TF | Type | Entry | SL | Size | Distance |
|----|------|-------|-----|------|----------|
| 4h | demand | 26864.5 | 26779.75 | 84.75 pts | +38.5 above |
| 15m | demand | 26849.25 | 26806 | 43.25 pts | +24 above |
| 4h | supply | — | — | — | none within 100 pts |
| 15m | supply | — | — | — | none within 100 pts |

**Entry candidates:**

1. **Long @ 26849.25** (15m ChoCh demand) — SL 26806 · Risk 43.25 pts · TP 26979 (3R)
   - Confluence: overlaps 4h demand 26779.75–26864.5 ✓
   - Confluence: overlaps untouched FVG 26839–26866.25 ✓
   - Size note: tight zone (43 pts) — favorable

2. **Long @ 26864.5** (4h BOS demand) — SL 26779.75 · Risk 84.75 pts · TP 27118.75 (3R)
   - Confluence: wraps 15m demand entirely ✓
   - Size note: wider zone (85 pts) — less favorable; prefer 15m if both trigger
```

If a symbol has **no unmitigated zones within 100 pts** in either direction, say so in one line and move on — do not invent zones.

## Context budget

- Target total output: one screen per symbol, ~400–600 bytes.
- Never dump the raw `data_get_structure_zones` JSON to the user. Summarize into the table + candidate bullets.
- Don't screenshot unless the user asks — the numeric report is sufficient.

## Rules (no exceptions)

1. Only trade **unmitigated** zones (`mitigated: false`). Never propose entries off mitigated zones.
2. Entry = `sol` (solid / ChoCh/BoS label price). SL = `dsh` (dashed pivot). TP = entry ± 3×risk. These come directly from `data_get_structure_zones`.
3. Zones are rectangles — always quote both edges.
4. FVG is confluence only. A zone without FVG overlap is still tradable; an FVG without a zone is not.
5. If 4h/15m is unclear (both consolidating, or conflicting trends with no same-direction confluence), ask before falling back to 1h/5m.
6. Do not import vocabulary from other strategies. No "bias," "PD Array," "indication," "correction," etc.
7. Tighter zones beat wider zones — always note size in the report.
