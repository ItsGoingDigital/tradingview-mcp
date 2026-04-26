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
3. Brief wait for indicator recompute (the tool returns `chart_ready` but primitives may lag ~1s — acceptable). When the symbol has just been switched, allow a few seconds before pulling data — otherwise studies may return `study_count: 0`.
4. `data_get_structure_zones` with `study_filter: "Market Structure"`, `within_points: 100` → returns all unmitigated zones within ±100 pts of current price, sorted nearest first. Each zone object: `{event, direction, zone_type, entry, sl, risk, tp_3R, size, bar_idx, mitigated}`.
5. `data_get_pine_boxes` with `study_filter: "FVG"` → returns live FVG zones as `{high, low}` arrays per FVG indicator instance.
6. `data_get_pine_labels` with `study_filter: "ICT Killzones"` → returns the ICT level set (PDH/PDL/PWH/PWL/PMH/PML/D Open/W Open/M Open/Midnight Open) as `{text, price}` pairs. Required for step 2.
7. `data_get_ohlcv` with `count: 60, summary: true` on the **15m timeframe** → today's session high/low (~15 hours, ≈ full futures session since 18:00 ET prior day). Required for step 2.
8. `quote_get` (already folded into `data_get_structure_zones.current_price`, but call separately if you need OHLC or description).

### 2. Verify today's session state (MANDATORY — do not skip)

**Without this check, any report that cites magnets or fresh zones is data-incorrect.** A swept level is not a magnet; buy-stops above or sell-stops below are already gone. A 3R target that the session has already traded past is a thesis that has already played out.

For each symbol, compute the session high and low from the 60-bar 15m OHLCV, then cross-check three things:

1. **Labels vs session range.** For each ICT label, compare to session high/low:
   - If label is *above* current price and session high ≥ label → label is **TAKEN**. Mark `(taken)` in the Liquidity section.
   - If label is *below* current price and session low ≤ label → label is **TAKEN**. Mark `(taken)` in the Liquidity section.
   - Otherwise → **alive**. This is a live magnet.

2. **Zone SL vs session range.** For each unmitigated zone, compare SL to session high/low:
   - Supply zone: if session high ≥ zone SL → **wick-tested**. Flag in the Zones table Note column.
   - Demand zone: if session low ≤ zone SL → **wick-tested**. Flag in the Zones table Note column.
   - A wick-tested zone is structurally weaker than a fresh zone. Downgrade grade accordingly.

3. **3R target vs session range.** For each proposed entry's `tp_3R`:
   - Short thesis: if session low ≤ tp_3R → the target has already been hit this session. The thesis has **already played out**.
   - Long thesis: if session high ≥ tp_3R → same, thesis already played out.
   - In either case, the trade is not a live setup. Re-frame as "move already completed" and either downgrade hard (D/F) or pass. Do not pitch a TP the session has already traded through.

**Morning red flag.** Friday and Monday mornings especially tend to have overnight/European moves that consume the clean liquidity before RTH. When running the skill between 06:00–10:00 ET, default to assuming levels may already be swept — the OHLCV check will confirm or reject.

### 3. Derive the trend per TF

Use the **sequence of the last ~6 BOS/ChoCh events** from `data_get_structure_zones` (pass `include_mitigated: true` for this step to see the recent history — then filter the analysis).

- **Up:** consecutive bullish BOS/ChoCh, making HH + HL.
- **Down:** consecutive bearish BOS/ChoCh, making LH + LL.
- **Consolidating:** alternating bullish/bearish within a tight range (no net new HH or LL).

If 4h and 15m both look consolidating, **stop and ask** the user: *"4h and 15m are consolidating — want me to analyze 1h and 5m instead?"*

### 4. Build entries

For each unmitigated zone returned by `data_get_structure_zones`, the tool has already computed:
- `entry` = solid line price
- `sl` = dashed line price
- `risk` = |entry − SL|
- `tp_3R` = entry ± 3×risk (+ for demand, − for supply)

Present entry/SL/TP **in points** (no dollar math). Note size (= risk in points) — smaller zones are preferred.

**TP realism check (ICT-level magnets).** The 3R target is arithmetic, not market reality. Build the magnet set from levels already pulled in step 1.6, plus three derived equilibriums:

- **Pulled levels:** PDH/PDL, PWH/PWL, PMH/PML, D Open, W Open, M Open, Midnight Open.
- **Derived equilibriums:** **PD-EQ** = (PDH + PDL) / 2 · **PW-EQ** = (PWH + PWL) / 2 · **PM-EQ** = (PMH + PML) / 2. Compute inline; not drawn by the indicator.

Scan the range between `entry` and `tp_3R` for any *alive* level (skip taken ones — they're not magnets anymore). Apply the same session-sweep rule from step 2 to the EQ levels: if session high/low has already traded through the EQ price, it's taken. Any alive hit inside the range is a likely reaction point that overrides the arithmetic 3R. Surface it in **The Trade** block as the realistic target; keep the 3R figure as the math reference. If multiple alive levels sit inside the range, the nearest one to entry is the primary TP, the next becomes the runner.

### 5. Check confluence

**FVG direction matters.** A bullish FVG is a gap created during an up-move and acts as future support — confluence for a long entry / demand zone. A bearish FVG is a gap created during a down-move and acts as future resistance — confluence for a short entry / supply zone. The Nephew_Sam indicator color-codes them: green/blue = bullish, red/orange = bearish. **A wrong-direction FVG over a zone is anti-confluence, not bonus.** Every FVG reference in the report must carry its direction prefix ("bullish FVG" / "bearish FVG"); a bare "FVG" reference is incomplete and fails review.

For each proposed entry, flag these (bullet per hit):
- **Cross-TF same-direction zone overlap:** a 4h demand zone overlaps a 15m demand zone if `[min(entry,sl), max(entry,sl)]` ranges intersect. Same for supply.
- **FVG overlap on same TF:** iterate the FVG `zones` array and flag if any same-direction FVG `[low, high]` intersects the S&D zone range. Note the direction in the flag ("bullish FVG below at X — Y").
- **Untouched FVG bonus:** Every FVG box still on chart is unmitigated by definition (Nephew_Sam removes mitigated ones) — that's not the bonus. The bonus is for **untouched same-direction** FVGs: price has not wicked back into the zone since it formed. Detect by comparing the FVG's `[low, high]` against the bar range since the FVG's creation — no overlap = untouched. Touched-but-unmitigated FVGs still count as plain FVG confluence; only untouched same-direction earns the bonus flag. A wrong-direction untouched FVG is not a bonus — flag it as a hazard if it sits between price and target.

#### Cluster check (high-probability reversal flag)

A **cluster** is the rare case where all three confluence factors stack inside a tight band. These are the highest-probability reversal points the strategy can identify. Check every symbol; expect most reports to find none.

A cluster exists when **all three** of the following sit within a tight band (defined below), in the **same direction**, and within 100 points of current price:

1. An **unmitigated S&D zone** (4h or 15m). Demand for a bullish cluster, supply for a bearish cluster.
2. An **untouched same-direction FVG** (bullish FVG for bullish cluster, bearish FVG for bearish cluster). Untouched per the bonus rule above — price has not wicked back into the FVG since it formed.
3. An **alive key level** (any of PDH/PDL, PWH/PWL, PMH/PML, Day Open, Week Open, Month Open, Midnight Open, or any EQ — PD-EQ, PW-EQ, PM-EQ).

**Tight band definition:** the zone is the anchor. The FVG must overlap the zone (any intersection counts). The key level must sit either inside the zone or within half the zone's width of the zone's nearest edge. Practically:

- Equity index futures (MES, MNQ, ES, NQ): typical qualifying bands are 10–20 points for 15m clusters, 30–60 points for 4h clusters.
- Metals (MGC, SIL, GC, SI): typical qualifying bands are 3–8 points for 15m, 10–20 for 4h.

Use the zone width as your reference, not a hard point cap. A 50-point 4h zone with a key level 20 points outside it is still tight if the half-zone-width rule allows it; an 11-point 15m zone with a key level 12 points outside fails.

**Same-direction rule:** bullish cluster means demand zone + bullish FVG + key level acting as a floor (or simply present in the band — direction matters for zone and FVG, not for the key level). Bearish cluster is the mirror. A wrong-direction FVG inside the zone does not break the cluster, but it must not be confused with the qualifying same-direction FVG.

**If a cluster is detected:** add a `**Cluster:**` callout in the per-symbol section between the Liquidity map and Zones table. List the three factors with prices, state the band width, and call it a high-probability reversal. Bump the setup grade one notch (B→A, A→A+; cap at A+) and note the cluster as the reason in Grade rationale.

**If no cluster:** omit the callout entirely. Do not write "no cluster found."

### 6. Closest zones section

Per TF: the **closest unmitigated demand below price** and the **closest unmitigated supply above price**. The tool's output is already sorted by distance from price — demand below is the nearest zone with `entry < current_price`, supply above is the nearest with `entry > current_price`. If there are none within 100 pts in a given direction, say so.

## Output template

**Deliverable.** Save each session as a standalone markdown file in `analysis/` using filename format `YYYY-MM-DD-HHMMET.md` (24-hour, timezone suffix, e.g. `2026-04-22-1326ET.md`). Multiple sessions per day are expected. The file is the finished product — written for a paying Discord subscriber, not an internal analyst.

**Canonical example:** see [`analysis/2026-04-22-1326ET.md`](../../analysis/2026-04-22-1326ET.md).

### Audience & voice

- **Audience:** hungry, eager-to-learn, eager-to-act traders paying premium for decisive counsel.
- **Voice:** informative, clear, decisive. Active voice. Short sentences. AP style.
- **Dates:** `April 22, 2026 · 1:26 p.m. ET` in prose. ISO in filenames.
- **Numbers:** numerals for all prices, points, sizes, grades.
- **AP style enforcement:**
  - Spell out "cross-timeframe" on first use; "cross-TF" allowed thereafter.
  - "Points" in prose ("11 points off the high"), "pts" in tables only. Don't mix in the same sentence.
  - Em dashes only when commas or parens won't work. Default to commas for parenthetical inserts.
  - Bullets must share parallel structure across the list. Either all fragments or all sentences, not mixed.
  - Spell out level abbreviations (PDH, PDL, PRE.H, MO, DO) on first use per symbol section, then abbreviate.
- **No hedges in directive lines.** Top Call, Call, and The Read commit. Banned: "either way," "scale in if you want," "roughly," "kind of," "maybe," "tactical" as a softener, "path is unclear" as a verdict. If a setup needs hedging, it does not belong as Top Call — demote it.

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
3. **Top Call** — blockquote with top pick's Entry · Stop · Target, then a thesis of **three sentences maximum**. The Top Call is the most decisive line in the document. No hedges: no "either way," no "scale in if you want," no "roughly," no "tactical" as a softener, no "if X happens, do Y; if not, do Z" branches. If the setup needs hedging to be defensible, it does not belong as the Top Call — demote it to a per-symbol section and pick a different top.
4. **The Board** — 7-col summary: Symbol · Grade · Call · Entry · Stop · Target · Risk. Top pick bolded in Symbol and Grade cells.
5. **Per-symbol sections** — identical structure across symbols (template below).
6. **Bottom Line** — decisive recap: one swing + grade, tacticals + grades, passes + grades. One-line risk reminder close.

### Per-symbol section (identical order every time)

```
## {TICKER} — {Description} · {price} · Grade {X}

**Trend:** 4h {Up/Down/Choppy} ({ICC phase}) · 15m {Up/Down/Choppy}
**Call:** **{GO LONG / GO SHORT / WATCH / PASS}** — {one-line verdict}
**Grade rationale:** {ONE sentence — comma-separated layers that aligned, plus one because-clause if held back from a higher grade. If it doesn't fit in one sentence, the rationale is wrong.}

**Liquidity map:** {one plain-English sentence — where the magnet still sits, which side got grabbed already, and where the day wants to go. Run it past the vocabulary check below before publishing.}

**Cluster:** {OPTIONAL — only when all three confluence factors stack inside a tight band per step 5's cluster check. Format: list the zone, the untouched same-direction FVG, and the alive key level with prices, state the band width, end with "high-probability reversal." Omit the line entirely when no cluster is detected — do not write "no cluster found."}

### Zones

| TF  | Type           | Range       | Size    | Note                                          |
|-----|----------------|-------------|---------|-----------------------------------------------|
| 15m | Demand/Supply  | low — high  | X pts   | fresh / wick-tested (X high/low) / stacked   |
| 4h  | Demand/Supply  | low — high  | X pts   | …                                             |

Optional note below table: "Zones overlap at X — X" (cross-timeframe stack).

**Note column is mandatory.** Every zone must be flagged as `fresh` or `wick-tested (X)` per step 2 of the workflow. FVG overlap and cross-timeframe stack go here too. **FVG references in the Note column must carry direction:** `bullish FVG below at X — Y` or `bearish FVG above at X — Y`. A bare "FVG" reference fails review.

### Liquidity

Every level cited must carry `(taken)` or `(alive)` per step 2 of the workflow. A level without a status marker fails the mandatory sweep check. Use only `(taken)` or `(alive)`; do not stack qualifiers like `(taken overnight, spent)` — the word "spent" belongs in the Liquidity map prose, not the data list.

Structure each side as a **magnet line** plus a **supporting line**:

- **Magnet above:** {single bolded alive level the day is reaching for, with one-clause reason. One level.}
- **Above (other levels):** previous day high (PDH) X (taken/alive) · previous week high (PWH) X (taken/alive) · Midnight Open X (taken/alive) · …
- **Magnet below:** {single bolded alive level the day is reaching for downside, with one-clause reason. One level.}
- **Below (other levels):** Day Open X (taken/alive) · previous day low (PDL) X (taken/alive) · Month Open X (taken/alive) · previous week low (PWL) X (taken/alive) · …

**Key level naming (canonical forms):**
- `PDH` / `PDL` = previous day high / low
- `PWH` / `PWL` = previous week high / low
- `PMH` / `PML` = previous month high / low
- `LON.H` / `LON.L` = London high / low
- `PRE.H` / `PRE.L` = pre-market high / low
- `Day Open`, `Week Open`, `Month Open`, `Midnight Open` — always spelled out, title case. **Never** use the all-caps indicator forms (`D OPEN`, `M OPEN`, `W OPEN`) in reports.
- EQ levels: `PD-EQ`, `PW-EQ`, `PM-EQ` — derived as the midpoint of the corresponding high/low pair.

**Not real key levels — do not cite as such:**
- `SB` / `SB.H` / `SB.L` — silver bullet window highs/lows are skill-specific session marks, not S&D key levels. Exclude from Liquidity sections.
- `PWR` — not a recognized level abbreviation. If the indicator outputs it, treat as noise.

If both extremes are taken and there is no clean magnet, write `**Magnet:** none — both sides spent` and skip the magnet split. Use the supporting lines as a flat reference list in that case.

### The Trade

- **Entry:** X — {zone reference}
- **Stop:** X — {invalidation}
- **Target:** X — {nearest alive ICT magnet inside entry→3R range, or the 3R figure if none}
- **3R reference:** X (only when Target ≠ 3R; omit the line entirely when Target and 3R agree to within a tick)
- **Risk / Reward:** X pts / X pts
- **Runner target (optional):** X — {next alive magnet beyond Target}
- **Confluence:** {bullish/bearish FVG with direction stated · cross-TF stack · untouched flag. Bare "FVG" is not allowed.}

### The Read

{Exactly two sentences. Sentence 1: the structural reason this setup works. Sentence 2: the condition that kills it. No restating Liquidity map, Grade rationale, or The Trade content. No hedges.}
```

### Liquidity map (per symbol)

One sentence, plain English, no jargon-stacking. Built from step 2's outputs (taken vs. alive labels) and the 4h trend. The job: tell the reader, in the language a smart trader would use over coffee, *which magnet is still pulling price today and which one is already spent*. Two anchors:

- **Where the unfinished business is** — the still-untouched PDH or PDL (or PWH/PWL if the daily extreme is already gone). Call it "the magnet" or "the unfinished business," not "the liquidity pool."
- **Whether the magnet is a reversal point or a continuation point** — driven by the 4h trend. Up trend + price reaching down = pullback buy; up trend + price reaching up = continuation; flip for down trend.

Examples (use this voice):
- *Yesterday's high at 21,180 is still untouched — that's where the day wants to go. Yesterday's low got swept overnight, so the downside pull is spent. 4h uptrend says price grabs that high and keeps going, doesn't reverse off it.*
- *Both ends of yesterday's range are gone already — high taken at the open, low taken in Asia. No clean magnet left; expect chop or a reach for last week's high at 21,420 if anything.*
- *PDL 4,180 still alive, sitting 22 points below price — that's the magnet. 4h downtrend means a sweep there is likely a continuation lower, not a bounce.*

#### Vocabulary check (mandatory before publishing)

Run every Liquidity map sentence past this check. If any banned phrase appears, rewrite. No exceptions.

**Banned phrases — replace before publishing:**
- "liquidity pool" → "the magnet"
- "stop run" → "sweep" or "grab"
- "bias" → just state the direction ("4h uptrend says…")
- "draw on liquidity" → "the magnet"
- "path of least resistance" → "wants to reach for X"
- "the bigger pull" / "the smaller pull" → "the magnet" (one magnet per side, not two)
- "first downside magnet" / "first upside magnet" → just "the magnet" (the supporting list handles the rest)
- "wants to poke" → "wants to reach for" / "wants to grab"
- "between magnets" → describe the actual condition, e.g. "stuck on PDL with PDH alive above"
- "where price wants to go" → "wants to reach for X"
- Any made-up compound term ("downside-magnet-cluster," "stop-pool-shelf") → don't.

**Approved vocabulary:**
- For the live level: "the magnet," "the unfinished business," "still untouched," "still alive."
- For the dead level: "already grabbed," "already swept," "spent."
- For the directional read: "wants to reach for," "wants to grab," "keeps going past it," "reverses off it."

**Self-check before publishing the report:**
1. Read each Liquidity map sentence aloud once. If any banned phrase is in it, rewrite.
2. Confirm only one magnet is named per side.
3. Confirm the directional read (continuation vs. reversal) is tied to the 4h trend, not invented.

### ICC phase (4h only)

Append the ICC phase to the 4h trend label in parentheses, with the indication, TP, and invalidation prices for reader reference: `4h Up (Continuation · ind 24420 · TP 24780 · inv 24180)`. Do **not** add it to the 15m — it gets confusing. Phases: Indication · Correction · Continuation · No Trade (choppy). See [`docs/strategies/icc.md`](../../docs/strategies/icc.md) for definitions. Reference only — does not affect grading or the S&D Call.

**What `ind`, `TP`, and `inv` actually mean — get these right or don't include them:**

- **`ind` = the previous 4h pivot level that was broken** to confirm the current trend (a previous PHH for an uptrend, a previous PLL for a downtrend). Historical level, already printed on the chart.
- **`TP` = the new extreme that price made on the move that broke `ind`** — the resulting new HH (bullish) or new LL (bearish). Historical level, already printed. **Not a fib extension, not an arithmetic projection, not a magnet estimate.** Just the actual high or low that resulted from the indication break. **TP only exists once a pullback has crystallized the extreme as a pivot** — during Indication phase, price is still extending and the TP is undefined. Show as `TP forming` (or omit) until the first pullback prints.
- **`inv` = the previous 4h PHL (bullish) or PLH (bearish), one pivot back from the most recent.** Historical level. The most recent PHL/PLH is the correction low/high being formed in the current cycle; the invalidation is the one *before* that. If `inv` breaks, the HH/HL or LH/LL pattern is dead and ICC stops applying. **`inv` is structural — it is not the stop loss.** The SL lives on 15m micro-structure; `inv` lives on 4h trend structure. Never conflate them.
- When price eventually exceeds the TP, the cycle rolls over: the old TP becomes the new `ind`, the next new extreme becomes the next TP (after its own pullback), and phase resets to Indication. `inv` only updates when a fresh PHL/PLH crystallizes and the prior one moves into the invalidation slot.

**Phase must be consistent with where current price sits relative to `ind` and `TP`:**

- **Indication** — price is at or near the new extreme, no pullback yet. TP is forming. Distance from current price to the working high/low is small.
- **Correction** — price has pulled back from the TP toward (or past) `ind`. Current price sits between TP and `inv`, often deep into the leg.
- **Continuation** — price has reclaimed `ind` and is moving back toward TP. The 15m has flipped in trend direction.
- **No Trade** — 4h is choppy; do not list any ICC levels.

If the numbers and the phase contradict (e.g. labeling phase = Indication while current price is hundreds of points away from the working extreme, or listing a fixed TP during Indication), the report is wrong. Either rederive the phase from the levels, or rederive the levels from the actual recent 4h pivot structure.

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
8. **MANDATORY session-sweep check (step 2).** Before publishing, pull 60-bar 15m OHLCV and cross-check every cited label, zone SL, and 3R target against session high/low. Mark every label `(taken)` or `(alive)`. Mark every zone `fresh` or `wick-tested`. If a 3R target has already been traded through this session, the trade is not live — downgrade or pass. A report missing these markers is data-incorrect. Skipping this check has cost real money (see `feedback_verify_swept_levels.md` in memory).
