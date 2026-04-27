---
name: chart-read
description: Read the latest chart-data snapshot for each symbol and produce a decision-ready playbook. Answers three market-reading questions per symbol — trend, magnet, reaction zones — and translates them into a tradeable form. Does not pull from the chart. Use when the user asks for the playbook, S&D analysis, "what's my setup," or any decision-grade output that builds on chart-data snapshots.
---

# chart-read — analysis on top of trusted facts

This skill consumes `chart-data` snapshots from `analysis/data/` and produces the full futures playbook. It does not invoke any chart-pulling tool. If the snapshot is missing, stale, or inconsistent, the right move is to surface the problem and ask the user to run `chart-data` again — never re-pull silently.

The analytical spine is three questions, asked per symbol:

1. **Is price trending up, down, or consolidating?**
2. **Where is price being pulled to?** (the magnet)
3. **Where is price likely to react?** (confluence; untouched same-direction FVG = bonus)

Trade construction (entry, structural protection, R-multiples, grade, Call) is the *expression* of those three answers in tradeable form. The Trade block, Grade, Call, Liquidity map prose, and Top Call selection all derive from the three questions — they are not a separate analytical step.

## Vocabulary

- **Trend:** Up / Down / Consolidating per timeframe.
- **Phase (4h ICC):** Indication / Correction / Continuation / No Trade. Classified from the snapshot's ind / TP / inv values + current price.
- **Magnet:** the single alive level per side that price is reaching for. One per side. No "the bigger pull / the smaller pull"; no compound terms.
- **Confluence:** unmitigated zone + same-direction FVG + alive key level inside a tight band. Untouched same-direction FVG is a bonus flag.
- **Cluster:** all three confluence factors stacked tight in the same direction. Rare. High-probability reversal signal.
- **Grade:** A / B / C / D / F. Reflects setup confluence quality. Does not override the Call — it informs sizing.
- **Call:** GO LONG / GO SHORT / WATCH / PASS.

## Inputs

- Latest `chart-data` snapshot per symbol from `analysis/data/`. Filename pattern: `YYYY-MM-DD-HHMMET-{SYMBOL}.md`.
- Default symbols (unless user overrides): MNQ, MES, MGC, SIL.

## Freshness gate (mandatory)

Before reading any snapshot:

1. For each symbol, find the most recent snapshot file under `analysis/data/`. If no snapshot exists for a default symbol, prompt: *"No chart-data snapshot found for {SYMBOL}. Run chart-data first."* — do not proceed for that symbol.
2. Compute snapshot age = current time − snapshot timestamp.
3. If age > 15 minutes, prompt: *"Snapshot for {SYMBOL} is {N} minutes old. Refresh chart-data?"* — do not proceed without explicit user direction.
4. If the snapshot has any failed-gate notes, surface them to the user and pause for direction before using that symbol.

## Workflow

### Stage 1 — load & triage

For each default symbol:

1. Read the latest snapshot.
2. Apply triage rules (cheap, no analysis depth):
   - **Zone present?** At least one unmitigated zone within range in the snapshot.
   - **Aligned magnet alive?** For supply (short setup), at least one alive key level below price within roughly 3R of the zone's lower edge. For demand (long setup), an alive key level above price within 3R of the upper edge. (3R math is computed in Stage 2; for triage, use the zone size × 3 as a coarse range.)
   - **Daily-extreme sanity.** If the only overhead magnets in a long's path are PDH and PWH and both are taken, skip with verdict "both extremes spent." Mirror for shorts.
3. Build the triage table (Symbol, Price, Zone summary, Aligned magnet, Verdict). Verdicts: `CANDIDATE`, `SKIP — no zone in range`, `SKIP — both extremes spent`, `SKIP — no aligned magnet alive`.

Skipped symbols carry to the Board with a one-line skip reason. Candidates proceed to Stage 2.

### Stage 2 — three-question pass per candidate

For each candidate, answer in this order:

#### 2.1 Trend (per TF)

Use the snapshot's ICC structural levels and any cycle context:

- **Up:** consecutive bullish BOS/ChoCh; price making HH + HL.
- **Down:** consecutive bearish BOS/ChoCh; price making LH + LL.
- **Consolidating:** alternating events within a tight range; no net new HH or LL.

If 4h is consolidating across all candidates, ask: *"4h is consolidating across candidates — drop to 1h instead?"*

#### 2.2 Phase classification (4h)

From the snapshot's ind / TP / inv + current price:

- **Indication** — price near working extreme; TP "forming" in the snapshot.
- **Correction** — price has pulled back from TP toward (or past) ind; TP is a numeric pivot in the snapshot.
- **Continuation** — price has reclaimed ind heading back toward TP; TP is a numeric pivot.
- **No Trade** — 4h is choppy; do not list ICC levels in the trend label.

**Phase consistency check (mandatory).** If the snapshot's TP is "forming" and you classify Correction or Continuation, stop — the snapshot is internally inconsistent or your phase pick is wrong. Re-derive the phase from the level math, or surface the data inconsistency to the user.

#### 2.3 Magnet identification

From the snapshot's alive key levels:

- **Magnet above:** the single closest alive level above current price that price is reaching for.
- **Magnet below:** the single closest alive level below.
- One per side. If both extremes are taken and no clean magnet exists, write `Magnet: none — both sides spent`.

Magnet choice is informed by 4h trend: in an uptrend reaching up, the upside magnet is a continuation target; reaching down, it's a pullback buy. Mirror for downtrend.

#### 2.4 Reaction zones (confluence + cluster)

For each unmitigated zone in the snapshot:

- Pair with same-direction FVGs that overlap the zone range (snapshot already labels FVG direction).
- Note any wrong-direction FVG between price and the zone — that's a hazard, not bonus.
- Note alive key levels inside the zone or adjacent (within half the zone's width).

**Cluster check:** an unmitigated zone + an untouched same-direction FVG + an alive key level, all stacked inside a tight band per the geometry rules below.

**Tight band:** the zone is the anchor. The FVG must overlap the zone. The key level must sit inside the zone or within half the zone's width of the nearest edge.

- Equity index futures (MES, MNQ): typical qualifying bands 10–20 pts (15m), 30–60 pts (4h)
- Metals (MGC, SIL): 3–8 pts (15m), 10–20 pts (4h)

If a cluster is detected, note it for the per-symbol section and bump grade one notch (capped at A+).

### Stage 3 — trade construction

For each candidate's chosen zone (if a tradeable setup exists):

1. **Pick the entry edge.** For shorts: lower zone edge. For longs: upper zone edge. The opposite edge is structural protection.
2. **Compute risk and 3R.** `risk = |edge_upper − edge_lower|`. For shorts, `tp_3R = entry − 3 × risk`. For longs, `entry + 3 × risk`.
3. **3R-already-traded check.** Compare `tp_3R` to the snapshot's session high/low:
   - Short with `session_low ≤ tp_3R` → move already delivered → downgrade hard (D/F) or pass.
   - Long with `session_high ≥ tp_3R` → same. Do not pitch a TP the session has already traded through.
4. **Magnet-overrides-3R.** Scan the entry-to-3R range for alive key levels. The nearest alive level inside the range is the realistic Target; keep the 3R figure as math reference only (omit the line if Target == 3R). If none inside the range, Target = 3R.
5. **Runner.** The next alive magnet beyond Target.
6. **Hazard scan.** Wrong-direction FVGs between entry and Target → list as hazards in The Trade Confluence line.
7. **Cross-TF stack.** A 4h zone overlapping a 15m zone in the same direction is a stack — note it.

### Stage 4 — grade & Call

Apply the grading rubric:

- **A** — every layer aligns: trend, cross-TF stack, tight size, alive magnet, fresh setup. Full size.
- **B** — strong setup missing one confluence. Standard size.
- **C** — tradeable with a known risk (counter-trend, no stack, wide zone). Reduce size or shorten hold.
- **D** — valid structure, thesis has a gap (usually missing magnet). Watch only.
- **F** — pass.

Use `+` / `-` modifiers for exceptional features. Cluster bumps grade one notch (capped at A+).

Call: GO LONG / GO SHORT / WATCH / PASS based on grade and trend alignment.

### Stage 5 — compose the playbook

Save to `analysis/YYYY-MM-DD-HHMMET.md` (24-hour, ET suffix).

**Document structure (in order):**

1. **Header** — `# Futures Playbook` + bold date/time + one-line vibe check (no hedges).
2. **Setup Grades legend** — A/B/C/D/F rubric verbatim.
3. **Top Call** — blockquote with Entry · Stop · Target, then a thesis of three sentences max. No hedges. If no candidate qualifies, write `**Top Call:** none — all symbols skipped at triage`.
4. **The Board** — 7-col summary: Symbol · Grade · Call · Entry · Stop · Target · Risk. One row per default symbol including skips. Top pick bolded.
5. **Per-symbol sections** — only for Stage 2 candidates. Skips do not get a per-symbol section.
6. **Bottom Line** — decisive recap: swing + grade, tacticals + grades, skips + grades + reasons.

### Per-symbol section template

```
## {TICKER} — {Description} · {price} · Grade {X}

**Trend:** 4h {Up/Down/Consolidating} ({phase} · ind {price} · TP {price or "forming"} · inv {price}) · 15m {Up/Down/Consolidating}
**Call:** **{GO LONG / GO SHORT / WATCH / PASS}** — {one-line verdict}
**Grade rationale:** {one sentence — comma-separated layers that aligned, plus one because-clause if held back from a higher grade}

**Liquidity map:** {one plain-English sentence — which magnet is alive, which is spent, where the day wants to go. Run it past the vocabulary check below.}

**Cluster:** {OPTIONAL — only when all three factors stack tight per Stage 2.4. Format: list zone, untouched same-direction FVG, alive key level with prices, state band width, end with "high-probability reversal." Omit entirely when no cluster.}

### Zones

| TF  | Type           | Range       | Size    | Note                                          |
|-----|----------------|-------------|---------|-----------------------------------------------|
| 15m | Demand/Supply  | low — high  | X pts   | FVG overlap / cross-TF stack                  |
| 4h  | Demand/Supply  | low — high  | X pts   | …                                             |

Optional note below table: "Zones overlap at X — X" (cross-timeframe stack).

FVG references in Note column must carry direction: `bullish FVG below at X — Y` or `bearish FVG above at X — Y`. A bare "FVG" reference fails review.

### Liquidity

- **Magnet above:** {single bolded alive level the day is reaching for, with one-clause reason}
- **Above (other levels):** PDH X (taken/alive) · PWH X (taken/alive) · …
- **Magnet below:** {single bolded alive level downside, with one-clause reason}
- **Below (other levels):** Day Open X (taken/alive) · PDL X (taken/alive) · …

If both extremes taken, write `**Magnet:** none — both sides spent` and skip the magnet split.

### The Trade

- **Entry:** X — {zone reference}
- **Stop:** X — {invalidation, structural protection edge of the zone}
- **Target:** X — {nearest alive magnet inside entry→3R range, or the 3R figure if none}
- **3R reference:** X (only when Target ≠ 3R; omit when they agree to within a tick)
- **Risk / Reward:** X pts / X pts
- **Runner target (optional):** X — {next alive magnet beyond Target}
- **Confluence:** {bullish/bearish FVG with direction · cross-TF stack · untouched flag · hazard FVGs if any}

### The Read

{Exactly two sentences. Sentence 1: the structural reason this setup works. Sentence 2: the condition that kills it. No restating Liquidity map, Grade rationale, or The Trade content. No hedges.}
```

## Liquidity map vocabulary check (mandatory)

Run every Liquidity map sentence past this. If any banned phrase appears, rewrite.

**Banned:**
- "liquidity pool" → "the magnet"
- "stop run" → "sweep" or "grab"
- "bias" → just state direction ("4h uptrend says…")
- "draw on liquidity" → "the magnet"
- "path of least resistance" → "wants to reach for X"
- "the bigger pull" / "the smaller pull" → "the magnet" (one per side)
- "first downside magnet" / "first upside magnet" → just "the magnet"
- "wants to poke" → "wants to reach for" / "wants to grab"
- "where price wants to go" → "wants to reach for X"
- Any made-up compound term ("downside-magnet-cluster," etc.) → don't.

**Approved:**
- For the live level: "the magnet," "the unfinished business," "still untouched," "still alive."
- For the dead level: "already grabbed," "already swept," "spent."
- For directional read: "wants to reach for," "wants to grab," "keeps going past it," "reverses off it."

**Self-check before publishing:**
1. Read each Liquidity map sentence aloud once. If any banned phrase, rewrite.
2. Confirm only one magnet per side.
3. Confirm directional read is tied to 4h trend.

## AP style enforcement

- Active voice. Short sentences.
- Numerals for prices, points, sizes, grades.
- Spell out "cross-timeframe" on first use; "cross-TF" thereafter.
- "Points" in prose; "pts" in tables only.
- Spell out abbreviations (PDH, PDL, PRE.H, MO, DO) on first use per symbol section, then abbreviate.
- Em dashes only when commas/parens won't work.
- Bullets must share parallel structure across the list.
- No hedges in directive lines (Top Call, Call, The Read). Banned: "either way," "scale in if you want," "roughly," "kind of," "maybe," "tactical" as a softener, "path is unclear" as a verdict.

## Rules (no exceptions)

1. **Never pull from the chart.** No `chart_*`, `data_get_*`, `tv_*` MCP calls. The snapshot is the only source. If you want a number that isn't in the snapshot, prompt the user to refresh chart-data.

2. **Trust the snapshot's sweep status.** Don't re-classify whether a label is taken/alive — that decision was made under the verified session window in chart-data. Re-classifying it here breaks the audit trail.

3. **Trust the snapshot's ICC ind/TP/inv.** Phase classification is yours; the underlying levels are not.

4. **Phase ↔ TP consistency is non-negotiable.** Correction and Continuation require numeric TP from the snapshot. If the snapshot says "TP forming," the only valid phases are Indication or No Trade.

5. **Every cited number must trace to the snapshot.** If you write "PDH 76.67 (alive)" in the playbook, that exact value with that exact status must appear in the snapshot.

6. **One magnet per side.** No compound, no stacked language. The supporting list handles the rest.

7. **Top Call must be a Stage 2 candidate.** No hedges. If no candidate qualifies, the document has no Top Call.

8. **Skipped symbols get a Board row only.** No per-symbol section. Do not invent zones or levels for them.

9. **Cluster claims require all three factors verified in the snapshot.** Zone unmitigated, FVG direction tagged + untouched=yes, key level alive. Any one missing → no cluster.
