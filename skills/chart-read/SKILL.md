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
   - **Daily-extreme sanity.** If the only overhead magnets in a long's path are PDH and PWH and both are taken, skip with verdict "both extremes spent." Mirror for shorts.
3. Build the triage table (Symbol, Price, Zone summary, Aligned magnet, Verdict). Verdicts: `CANDIDATE`, `SKIP — no zone in range`, `SKIP — both extremes spent`, `SKIP — no aligned magnet alive`.

Skipped symbols carry to the Board with a one-line skip reason. Candidates proceed to Stage 2.

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
- **Watch for:** {one or two complete sentences describing the specific session-level signal that activates the trade and the level or behavior that disproves the read. AP Style.}

If both extremes are taken, write `**Magnet:** none — both sides spent` and skip the magnet split. The "Watch for" bullet is mandatory on every candidate.

### The Trade

- **Entry:** X — {zone reference, fragment OK}
- **Stop:** X — {invalidation, structural protection edge of the zone}
- **Target:** X — {nearest alive magnet inside entry→3R range, or the 3R figure if none}
- **3R reference:** X (only when Target ≠ 3R; omit when they agree to within a tick)
- **Risk / Reward:** X pts / X pts (≈ XR)
- **Runner target:** X — {next alive magnet beyond Target} (omit if no runner)
- **Confluence:** {one complete sentence naming the same-direction FVG with prices and direction, alive key levels inside or adjacent to the zone, and cross-timeframe stack if present. No ICC vocabulary.}
- **Hazards:** {one complete sentence naming wrong-direction FVGs between entry and target with prices and count, or "None — clean path." No ICC vocabulary.}

### The Read

{Three or four complete sentences walking the reader through the setup. AP Style. Active voice. No ICC vocabulary. No restating the Grade rationale or The Trade content verbatim.

Sentence 1 — structural framing: where price sits relative to the controlling zone and what the recent S&D structure shows.
Sentence 2 — confluence: the same-direction FVG overlap, alive key levels inside or adjacent to the zone, and any cross-timeframe stack.
Sentence 3 — trigger: the specific session-level signal that activates the trade.
Sentence 4 — invalidation: the level or behavior that disproves the read.}
```

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
