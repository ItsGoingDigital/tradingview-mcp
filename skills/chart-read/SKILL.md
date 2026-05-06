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

- **Trend:** Up / Down / Consolidating per timeframe. Derived from market structure (HH/HL for Up, LH/LL for Down) — *not* from ICC events.
- **Phase (4h ICC) — reference only:** Indication / Correction / Continuation / No Trade. Classified from the snapshot's ind / TP / inv values + current price. Output on the 4h trend line for the reader. **Never used as a Call driver, grade input, tiebreaker, or confluence factor.** S&D structure (zones + FVGs + alive key levels + market structure) is what drives the read.
- **Magnet:** the single alive level per side that price is reaching for. One per side. No "the bigger pull / the smaller pull"; no compound terms.
- **Confluence:** unmitigated zone + same-direction FVG + alive key level inside a tight band. Untouched same-direction FVG is a bonus flag.
- **Cluster:** all three confluence factors stacked tight in the same direction. Rare. High-probability reversal signal.
- **Grade:** A / B / C / D / F. Reflects setup confluence quality. Does not override the Call — it informs sizing.
- **Call:** GO LONG / GO SHORT / WATCH / PASS.

## Inputs

- Latest `chart-data` snapshot per symbol from `analysis/data/`. Filename pattern: `YYYY-MM-DD-HHMMET-{SYMBOL}.md`.
- Default symbols (unless user overrides): MNQ, MES, MGC, SIL.

## Arguments

- **`appendix`** (boolean, default `false`) — when invoked with `appendix=true`, `--appendix`, or simply `appendix`, append a per-symbol ICC Appendix to the playbook. Reference output only; never affects Call, Grade, magnet pick, or any analytical decision. See Stage 6 below.

## Freshness gate (mandatory)

Before reading any snapshot:

1. For each symbol, find the most recent snapshot file under `analysis/data/`. If no snapshot exists for a default symbol, prompt: *"No chart-data snapshot found for {SYMBOL}. Run chart-data first."* — do not proceed for that symbol.
2. Compute snapshot age = current time − snapshot timestamp.
3. If age > 60 minutes, prompt: *"Snapshot for {SYMBOL} is {N} minutes old. Refresh chart-data?"* — do not proceed without explicit user direction.
4. If the snapshot has any failed-gate notes, surface them to the user and pause for direction before using that symbol.

## Workflow

### Stage 1 — load & triage

For each default symbol:

1. Read the latest snapshot.
2. Apply triage rules (cheap, no analysis depth):
   - **Zone present?** At least one unmitigated zone within range in the snapshot.
   - **Aligned magnet alive?** For supply (short setup), at least one alive key level below price within roughly 3R of the zone's lower edge. For demand (long setup), an alive key level above price within 3R of the upper edge. (3R math is computed in Stage 2; for triage, use the zone size × 3 as a coarse range.)
   - **Daily-extreme sanity.** If the only overhead magnets in a long's path are PDH and PWH and both are taken, *do not skip outright* — flag the symbol as `EXTENDED` and route to break-and-go evaluation (Stage 3.5). Mirror for shorts. Skip only if break-and-go also has no clean structural anchor.
3. Build the triage table (Symbol, Price, Zone summary, Aligned magnet, Verdict). Verdicts: `CANDIDATE` (retest path viable), `EXTENDED` (overhead/underside spent → break-and-go evaluation), `SKIP — no zone in range`, `SKIP — no structural anchor`.

`CANDIDATE` and `EXTENDED` symbols both proceed to Stage 2. Skips carry to the Board with a one-line reason.

### Stage 2 — three-question pass per candidate

For each candidate, answer in this order:

#### 2.1 Trend (per TF) — drives the read

Derive trend strictly from S&D market structure on the snapshot:

- **Up:** consecutive bullish BOS/ChoCh; HH + HL; the most recent unmitigated zone is demand below price.
- **Down:** consecutive bearish BOS/ChoCh; LH + LL; the most recent unmitigated zone is supply above price.
- **Consolidating:** alternating BOS/ChoCh inside a tight range; zones on both sides of price; no net new HH or LL.

Market structure (BOS/ChoCh, swing pivots, zone direction) is valid evidence. ICC *phase* (Indication / Correction / Continuation) is **not** valid trend or bias evidence — keep it confined to the reference output in Stage 2.2.

If 4h is consolidating across all candidates, ask: *"4h is consolidating across candidates — drop to 1h instead?"*

#### 2.2 ICC phase (4h) — reference only, not a driver

ICC levels and phase are output on the 4h trend line for the reader. They have **zero bearing** on the Call, the grade, or directional bias. Do not use them as a tiebreaker, a confluence factor, or to justify the read in The Read / Liquidity map / Grade rationale.

From the snapshot's ind / TP / inv + current price, classify the 4h phase for the reference label:

- **Indication** — price near working extreme; TP "forming" in the snapshot.
- **Correction** — price has pulled back from TP toward (or past) ind; TP is a numeric pivot in the snapshot.
- **Continuation** — price has reclaimed ind heading back toward TP; TP is a numeric pivot.
- **No Trade** — 4h is choppy; do not list ICC levels in the trend label.

**Phase consistency check (mandatory).** If the snapshot's TP is "forming" and you classify Correction or Continuation, stop — the snapshot is internally inconsistent or your phase pick is wrong. Re-derive the phase from the level math, or surface the data inconsistency to the user. (Phase still has zero bearing on the Call — this check is a data-integrity gate, not an analytical step.)

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

### Stage 3 — trade construction (retest path)

For each `CANDIDATE` symbol's chosen zone (if a tradeable retest exists):

1. **Pick the entry edge.** For shorts: lower zone edge. For longs: upper zone edge. The opposite edge is structural protection.
2. **Compute risk and 3R.** `risk = |edge_upper − edge_lower|`. For shorts, `tp_3R = entry − 3 × risk`. For longs, `entry + 3 × risk`.
3. **3R-already-traded check.** Compare `tp_3R` to the snapshot's session high/low:
   - Short with `session_low ≤ tp_3R` → move already delivered → consider Stage 3.5 (break-and-go) instead of pitching a spent retest.
   - Long with `session_high ≥ tp_3R` → same. Do not pitch a TP the session has already traded through; route to Stage 3.5.
4. **Magnet-overrides-3R.** Scan the entry-to-3R range for alive key levels. The nearest alive level inside the range is the realistic Target; keep the 3R figure as math reference only (omit the line if Target == 3R). If none inside the range, Target = 3R.
5. **Runner.** The next alive magnet beyond Target.
6. **Hazard scan.** Wrong-direction FVGs between entry and Target → list as hazards in The Trade Confluence line.
7. **Cross-TF stack.** A 4h zone overlapping a 15m zone in the same direction is a stack — note it.

### Stage 3.5 — trade construction (break-and-go path)

Use this path for `EXTENDED` symbols *and* for `CANDIDATE` symbols where Stage 3 step 3 (3R-already-traded) ruled out the retest. The premise: when momentum has carried price past the structural retest entry, a confirmation-on-break entry is the only realistic way to participate in continuation. This path is paired with the retest path, not a replacement — when both are viable, present both and let R/R decide the Top Call.

**Trigger conditions (all must hold):**

- 4h trend is `Up` or `Down` per Stage 2.1 (not `Consolidating` — break-and-go from chop is a fade, not a trend trade).
- The most recent 4h or 15m unmitigated zone is in the trend direction (bull demand below for longs; bear supply above for shorts) — confirms structure has not flipped.
- Session_high (long) or session_low (short) sits within 25% of zone size from current price — i.e., price is hovering near the breakout pivot, not 3R-extended already.
- A deeper alive magnet exists in the trend direction (PMH, PWH, or 4h FVG cluster for longs; PML, PWL for shorts). Without one, break-and-go has no target — skip.

**Construction:**

1. **Entry trigger.** 15-minute close beyond the breakout pivot:
   - Long: 15m close above session_high (or above the most recent 15m swing high if intraday already broke session_high).
   - Short: 15m close below session_low (or most recent 15m swing low).
2. **Entry price.** Mid-bar of the confirming 15-minute bar, or the breakout pivot itself for limit orders.
3. **Stop.** The most recent 15-minute swing low (long) or swing high (short) — *not* the 4h zone opposite edge. The 4h zone is too far away in an extended condition; using it as a stop blows up the R/R.
4. **Target.** First alive deep magnet in the trend direction. Examples: long → PMH, then PWH; short → PML, then PWL. Never invent a target — must be a snapshot-listed alive level.
5. **R/R math.** `risk = |entry − stop|`, `reward = |target − entry|`. Compute R/R; if reward < 1.5R, downgrade or skip — break-and-go demands at least 1.5R because the stop is a market-structure level, not a structural zone.
6. **Hazard scan.** Wrong-direction FVGs between entry and target are still hazards. Note count and location.
7. **No cross-TF stack.** Break-and-go entries do not get a cross-TF stack note — the entry is at a market-structure level, not a zone overlap. Stack notes belong only to retest entries.

**Why this is structurally weaker than retest:** the stop is at the most recent swing, which can be tagged on routine pullbacks. The retest path uses zone edges, which carry institutional weight. Cap break-and-go grade at B (B+ if there's a cluster of alive deep magnets stacked tight, but never A).

### Stage 4 — grade & Call

Apply the grading rubric:

- **A** — every layer aligns: trend, cross-TF stack, tight size, alive magnet, fresh setup. Full size. *Retest path only.*
- **B** — strong setup missing one confluence. Standard size. *Either path; break-and-go caps here unless a deep-magnet cluster lifts to B+.*
- **C** — tradeable with a known risk (counter-trend, no stack, wide zone, or break-and-go with marginal R/R). Reduce size or shorten hold.
- **D** — valid structure, thesis has a gap (usually missing magnet). Watch only.
- **F** — pass.

Use `+` / `-` modifiers for exceptional features. Cluster bumps grade one notch (capped at A+ for retest, B+ for break-and-go).

**Path-specific grading:**
- *Retest path:* normal rubric. Cluster, cross-TF stack, and structural-zone stop are eligible for A grades.
- *Break-and-go path:* maximum B+. The stop sits at a 15-minute swing rather than a structural zone, so the setup carries timing risk that retests do not. Even with a deep alive magnet and trend-aligned structure, the path-specific cap holds.

Call: GO LONG / GO SHORT / WATCH / PASS based on grade and trend alignment. When both retest and break-and-go are viable for the same symbol and direction, present both with the better R/R as primary and the other as alternate in The Trade section.

### Stage 5 — compose the playbook

Save to `analysis/YYYY-MM-DD-HHMMET.md` (24-hour, ET suffix).

**Document structure (in order):**

1. **Header** — `# Futures Playbook` + bold date/time + one-line vibe check (no hedges).
2. **Setup Grades legend** — A/B/C/D/F rubric verbatim.
3. **Top Call** — blockquote with Entry · Stop · Target, then a thesis of three sentences max. No hedges. If no candidate qualifies, write `**Top Call:** none — all symbols skipped at triage`.
4. **The Board** — 7-col summary: Symbol · Grade · Call · Entry · Stop · Target · Risk. One row per default symbol including skips. Top pick bolded.
5. **Per-symbol sections** — only for Stage 2 candidates. Skips do not get a per-symbol section.
6. **Bottom Line** — decisive recap: swing + grade, tacticals + grades, skips + grades + reasons.
7. **Appendix — ICC Reference** — only when `appendix=true`. See Stage 6.

### Per-symbol section template

```
## {TICKER} — {Description} · {price} · Grade {X}

**Trend:** 4h {Up/Down/Consolidating} ({phase} · ind {price} · TP {price or "forming"} · inv {price}) · 15m {Up/Down/Consolidating}
**Call:** **{GO LONG / GO SHORT / WATCH / PASS}** — {one complete-sentence verdict; no hedges}
**Grade rationale:** {one or two complete sentences citing specific S&D layers that contributed (zones, FVG overlap, alive magnets, cross-timeframe stack) and the factor that held the grade back, if any. No ICC vocabulary.}

**Cluster:** {OPTIONAL — only when all three factors stack tight per Stage 2.4. Format: list zone, untouched same-direction FVG, alive key level with prices, state band width, end with "high-probability reversal." Omit entirely when no cluster.}

### Zones

| TF  | Type           | Range       | Size    | Note                                          |
|-----|----------------|-------------|---------|-----------------------------------------------|
| 15m | Demand/Supply  | low — high  | X pts   | {confluence note — FVG overlap with prices and direction, alive level inside zone, cross-TF stack}                |
| 4h  | Demand/Supply  | low — high  | X pts   | …                                             |

Optional note below table: "Zones overlap at X — X" (cross-timeframe stack).

FVG references in Note column must carry direction: `bullish FVG below at X — Y` or `bearish FVG above at X — Y`. A bare "FVG" reference fails review.

### Liquidity

{Lead paragraph — one or two complete sentences describing the directional pull for the session, anchored in S&D layers (which zone is controlling, which magnet the session is reaching for, which side is spent). AP Style. Active voice. No ICC vocabulary.}

- **Magnet above:** {price} (alive) — {standardized fragment naming the role: e.g., "first natural rejection inside the 4h supply"; "the deep-high magnet"; "first overhead target above the zone"}
- **Other above:** {price} ({alive/taken/distant}) · {price} ({status}) · …
- **Magnet below:** {price} (alive) — {standardized fragment naming the role}
- **Other below:** {price} ({status}) · {price} ({status}) · …
- **Watch for:** {one or two complete sentences describing the specific session-level signal that activates the trade and the level or behavior that disproves the read. For break-and-go entries, the activating signal is "a 15-minute close above/below {breakout level}." For retest entries, it is "a 15-minute rejection wick into {zone} with a close back through {edge}." AP Style.}

If both extremes are taken, write `**Magnet:** none — both sides spent` and skip the magnet split. The "Watch for" bullet is mandatory on every candidate.

### The Trade

- **Entry mode:** {Retest / Break-and-go / Retest primary + Break-and-go alternate}
- **Entry:** X — {zone reference for retest; "15m close beyond {breakout level}" for break-and-go}
- **Stop:** X — {opposite zone edge for retest; most recent 15m swing low/high for break-and-go}
- **Target:** X — {nearest alive magnet inside entry→3R range for retest; first alive deep magnet in trend direction for break-and-go}
- **3R reference:** X (retest only; omit for break-and-go since stop is market-structure-anchored)
- **Risk / Reward:** X pts / X pts (≈ XR)
- **Runner target:** X — {next alive magnet beyond Target} (omit if no runner)
- **Confluence:** {one complete sentence naming the same-direction FVG with prices and direction, alive key levels inside or adjacent to the zone, and cross-timeframe stack if present. No ICC vocabulary.}
- **Hazards:** {one complete sentence naming wrong-direction FVGs between entry and target with prices and count, or "None — clean path." No ICC vocabulary.}

**When both paths are viable**, append an `### Alternate trade` block under The Trade with the same structure for the secondary path.

### The Read

{Three or four complete sentences walking the reader through the setup. AP Style. Active voice. No ICC vocabulary. No restating the Grade rationale or The Trade content verbatim.

Sentence 1 — structural framing: where price sits relative to the controlling zone and what the recent S&D structure shows.
Sentence 2 — confluence: the same-direction FVG overlap, alive key levels inside or adjacent to the zone, and any cross-timeframe stack.
Sentence 3 — trigger: the specific session-level signal that activates the trade.
Sentence 4 — invalidation: the level or behavior that disproves the read.}
```

### Stage 6 — ICC Appendix (optional, reference-only)

**Trigger:** only when invoked with `appendix=true`. If the flag is not set, skip this stage entirely — the playbook ends after Bottom Line.

**Hard rule:** the Appendix is a reference snapshot for the reader. It must not influence the Top Call, Grade, magnet pick, or any analytical decision in Stages 1–5. If the Appendix changes the playbook's body, the skill ran wrong. Re-derive the body from S&D layers and put cycle context here only.

**Scope:** include every default symbol (MNQ, MES, MGC, SIL by default), even those that triage skipped or have partial / undetermined ICC values. Skipped symbols still get an Appendix entry — the Appendix is a *reference*, not gated on tradeability.

**Source of truth:** the snapshot's `## ICC structural levels (4h)` section. Read `ind`, `TP`, `inv`, and any working-extreme notes verbatim. Never re-derive levels here — the snapshot already did the math under the verified session window. If the snapshot says "undetermined this run," the Appendix entry says "undetermined" with a one-line note explaining why (typically: zone-pull window too narrow, no unmit zone in history, etc.).

**Phase classification (re-derived for the Appendix only, never copied to the per-symbol Trend line):**

- **Indication** — TP is "forming" in the snapshot; price sits in the impulse leg without a crystallized leg-extreme pivot. Working extreme is the candidate TP.
- **Correction** — TP is a numeric pivot; price has pulled back from TP toward (or past) ind. Trade frame is "retrace inside the cycle."
- **Continuation** — TP is a numeric pivot; price has reclaimed ind in the cycle direction and is heading back toward (or past) TP.
- **No Trade** — 4h is choppy, structure is unclear, or all three ICC levels are undetermined. List levels that exist; omit the rest.

Phase consistency check applies (Stage 2.2): Correction or Continuation require a numeric TP. If TP is "forming," the only valid Appendix phase labels are Indication or No Trade.

**Appendix structure:**

```
## Appendix — ICC Reference (4h)

> Reference output. ICC phase, ind, TP, and invalidation are read from the chart-data snapshot for context only. They do not influence the Top Call, Grade, magnet pick, or any analytical decision in this playbook.

### {TICKER} — {phase}

- **ind:** {price} — {one-line: which event broke this pivot, e.g., "broken pivot of bear ChoCh at bar_idx 1304" copied from snapshot}
- **TP:** {price or "forming"} — {one-line: leg extreme description; if "forming," include working-extreme value and the bar that printed it}
- **inv:** {price or "undetermined"} — {one-line: paired pivot of the BOS/ChoCh one back from the most recent in the same cycle direction}
- **Cycle direction:** {bull / bear / undetermined}
- **Phase reasoning:** {one or two sentences: cite the snapshot-level facts that yielded the phase pick — TP forming → Indication; TP numeric + price below ind in bear cycle → Correction; etc. No prose about "what the phase means for the trade." Keep it descriptive, not directive.}

**Correction levels addendum** — only when phase = Correction (mandatory per `feedback_correction_addendum_mandatory` memory).

The leg from {paired-pivot prior to TP} to TP spans {N} points. Reference fibs across the full leg:

- 38.2%: {price}
- 50.0%: {price}
- 61.8%: {price}
- 78.6%: {price}

{One-sentence factual note: where current price sits in the fib stack. No directional language.}
```

**Per-phase output rules:**

- **Indication:** show ind, TP forming with working extreme, inv (or "undetermined"). No Correction addendum.
- **Correction:** show ind, TP (numeric), inv. Include Correction levels addendum with full-leg fibs (per `feedback_fib_full_leg`: leg = swing low → swing high, not indication-to-TP).
- **Continuation:** show ind, TP (numeric), inv. Note where current price sits relative to ind and TP. No Correction addendum.
- **No Trade:** state phase = No Trade and list whatever levels exist. Skip phase reasoning if all three are undetermined; just say "structure has not yet established a fresh anchor; await new BOS or ChoCh."

**Vocabulary in the Appendix:** ICC vocabulary is permitted here (and only here, plus the per-symbol Trend line) — "Indication," "Correction," "Continuation," "ind," "TP," "inv," "bull cycle," "bear cycle," "leg," "broken pivot," "paired pivot." Stay descriptive. Do not write "the Correction phase suggests longs back from ind" — that's directive language and belongs nowhere in the playbook.

**Verification before publishing:**

1. Confirm the body of the playbook (Stages 1–5) does not reference the Appendix.
2. Confirm every Appendix value traces to the snapshot's `## ICC structural levels (4h)` section verbatim.
3. Confirm Correction phase entries carry the levels addendum.
4. Confirm No Trade entries do not invent phases or levels — they describe absence.

## Liquidity vocabulary check (mandatory)

Run every Liquidity lead-paragraph and Watch-for sentence past this. If any banned phrase appears, rewrite.

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

**ICC vocabulary banned in analytical prose** (Top Call thesis, Grade rationale, Liquidity lead, Watch for, The Trade Confluence/Hazards, The Read, Bottom Line). The 4h Trend line and the per-symbol header are the only places ICC may appear:
- "Indication phase" / "Correction phase" / "Continuation phase" → omit; cite the zone, FVG, and market-structure evidence instead.
- "ind" / "TP" / "inv" / "structural break point" / "broken pivot" → omit in prose; cite the zone edges and key-level prices instead.
- "bear cycle" / "bull cycle" / "ICC cycle" / "cycle direction" → "4h Down" / "4h Up" / "lower highs and lower lows" / "higher highs and higher lows."
- "retracing toward ind" / "retesting the broken pivot" → "retesting the unmitigated 4h supply" / "retesting the unmitigated 4h demand."

**Approved standardized vocabulary** — pick from this list and stick to it for predictability:
- For zones: "the unmitigated 4h supply at X — Y" / "the unmitigated 15m demand at X — Y" / "the controlling zone."
- For zone interactions: "wicks into," "rejects," "fails to hold," "reclaims," "mitigates," "respects."
- For FVGs: "bearish 4h FVG inside the zone at X — Y" / "bullish 15m FVG overlapping at X — Y." Direction tag mandatory.
- For levels: "PDH X (alive)," "PWH X (taken)," "the magnet at X," "still alive," "spent," "already grabbed," "already swept."
- For directional read: "wants to reach for," "wants to grab," "keeps going past it," "reverses off it."
- For trend: "lower highs and lower lows," "higher highs and higher lows," "alternating swings inside a tight range."
- For magnet roles in the bullet fragments: "first natural rejection inside the zone," "the deep-low magnet," "the deep-high magnet," "first overhead target," "first downside target."

**Style enforcement (mandatory):**
- Prose lines (Top Call thesis, Grade rationale, Liquidity lead, Watch for, Confluence, Hazards, The Read, Bottom Line) must be complete sentences, AP Style, active voice.
- Bullets in Liquidity, Trade, and Board may be fragments, but must use parallel structure within a list.
- Every cited level must carry its alive/taken status on first reference per per-symbol section.
- Spell out abbreviations (PDH, PDL, PWH, PWL, PMH, PML, MO, DO, WO, PD-EQ, PW-EQ, PM-EQ, FVG) on first use per per-symbol section, then abbreviate.

**Self-check before publishing:**
1. Read each prose sentence aloud once. If any banned phrase or fragment masquerading as a sentence, rewrite.
2. Confirm only one magnet per side.
3. Confirm directional read is tied to 4h trend evidence (zones + market structure), not to ICC phase language.
4. Confirm no ICC vocabulary appears outside the Trend line.

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

4a. **ICC is reference-only — never a driver.** ICC phase, ind, TP, and inv appear on the 4h trend line for the reader. They are forbidden as inputs to the Call, the grade, the magnet pick, the cluster check, the trade construction, or any directional read. The Grade rationale and The Read must justify the setup from S&D layers (market structure, zones, FVGs, alive key levels) only. If you find yourself writing "bear-cycle Correction tips the read short" — rewrite to cite the unmitigated supply zone, the bearish FVG, the alive downside magnet instead. Per `feedback_icc_levels_mandatory_in_snd` and `feedback_snd_strategy_purity` memories.

5. **Every cited number must trace to the snapshot.** If you write "PDH 76.67 (alive)" in the playbook, that exact value with that exact status must appear in the snapshot.

6. **One magnet per side.** No compound, no stacked language. The supporting list handles the rest.

7. **Top Call must be a Stage 2 candidate.** No hedges. If no candidate qualifies, the document has no Top Call.

8. **Skipped symbols get a Board row only.** No per-symbol section. Do not invent zones or levels for them.

9. **Cluster claims require all three factors verified in the snapshot.** Zone unmitigated, FVG direction tagged + untouched=yes, key level alive. Any one missing → no cluster.
