# The Top-Tick Framework — MNQ · April 23, 2026

**A case study and system for identifying session reversals at prior-day extremes**

Built on the ICT reversal framework ([docs/strategies/ict-reversals.md](../docs/strategies/ict-reversals.md)) and the Supply and Demand method ([skills/supply-demand/REFERENCE.md](../skills/supply-demand/REFERENCE.md)). This document treats both as inputs and distills a single actionable framework for top and bottom ticking.

---

## Executive Summary

On April 23, 2026, MNQ printed its session high at 27,156 at 11:30 a.m. ET and delivered from that high to 26,680 — a 476-point reversal that swept the prior-day low at 26,728. The top was callable in advance. The delivery to PDL was callable after the fact. Both are products of a repeatable sequence, not coincidence.

The sequence, stated plainly:

1. Price targeted the highest untouched liquidity pool in the dealing range (PDH 27,138).
2. Price swept it twice — first touch at 27,142.5, marginal new high at 27,156 — on declining volume.
3. The sweep occurred in the tail of the NY AM killzone and inside the London Close killzone (the classic reversal window).
4. There was no higher-priority liquidity above PDH; the prior-week high and prior-month high were below price. Upside was a liquidity void.
5. The first reversal leg produced a clean lower-timeframe CHoCH and a fresh bearish FVG that priced refused to reclaim.
6. The consolidation between 11:30 and 13:00 formed a lower high at 27,118 — the structural confirmation that the top was in.
7. The breakdown from that lower high carried through every downside reference level with no reaction, indicating a full delivery to PDL.

Each of these is definable. Each has explicit rules. The framework below encodes them.

---

## Part I — The Anatomy of the Move

All times Eastern. Levels are fact at time of print, taken from the 5m chart and the chart's ICT Killzones & Pivots indicator.

### Overnight and Premarket Context

| Level | Price | Status at 9:30 |
|-------|-------|----------------|
| PDH | 27,138 | Overhead — untouched |
| D OPEN | 27,080.75 | Overhead — untouched |
| PRE.H | 27,080 | Overhead — coincident with D OPEN |
| Midnight Open | 26,908 | Below — already traded through |
| PWH | 26,883 | Below — already traded through |
| PDL | 26,728 | Far below — untouched |
| PWL | 24,914.5 | Far below — structural |

Above price at the cash open: one cluster at 27,080 (three overlapping levels) and one isolated level at 27,138 (PDH). Below price: nothing structural inside 200 points. The asymmetry is critical. Buy-side liquidity was stacked and obvious. Sell-side liquidity was thin and distant.

### The Cash Open Drive (9:30–11:30)

- **9:30 open**: 27,004 after a pre-open SSL sweep to 26,964 on 39,580 volume. Displacement down, reversal immediate.
- **9:30–9:45**: Rally to 27,102, tagging the 27,080 cluster. Failure to hold above — close back inside at 27,058.
- **9:55–10:00**: Retracement to 26,966. Double-bottom with the 9:25 low. The session's structural floor.
- **10:31**: Bullish CHoCH → BOS confirmation on the 1m. Silver Bullet long at 27,036.5, stop 26,985, target 27,139.5.
- **11:10–11:15**: First sweep of PDH — high 27,142.5, close 27,137.5. The structural breakout.
- **11:15–11:20**: High 27,149.5. Minor pullback to 27,127.
- **11:19**: Silver Bullet 2R target filled at 27,139.5.
- **11:25–11:30**: **High of day 27,156**. A marginal new high, 6.5 points above the 11:20 high. Final stop-hunt before reversal.

At 11:30 the picture was: PDH swept twice, no further upside references, volume on the final push down from the cash-open drive, and the NY AM killzone closed.

### The Reversal Leg (11:30–11:45)

- **11:30–11:35**: Open 27,146.25, close 27,126.75. Red bar. First lower close since 10:35.
- **11:35–11:40**: Open 27,126.75, close 27,120. Continued selling, no reclaim of prior bar high.
- **11:40–11:45**: Open 27,120.5, close 27,091.5. Sharp drop — range 40 points, body 29 down. First close below D OPEN 27,080.75 not sustained (low 27,081.75).

The 11:30–11:45 sequence carried price 65 points off the HOD. This is the first leg of the reversal. It is not, on its own, proof of a delivery; it is proof that the HOD has held.

### The Consolidation (11:45–12:55) — The Decision Phase

For 70 minutes, price oscillated between 27,044 and 27,118. The dollar question during this window: did the market just take a breath before ripping higher, or did the delivery to PDL begin at 11:30?

Key events inside the window:

- **11:55**: Low 27,044.25. First test of the 11:40–11:45 leg low area.
- **12:05–12:10**: Rally to 27,082.75. Retest of D OPEN from below — rejection.
- **12:25–12:30**: **Second rally attempt — high 27,118.75.** Critical print. This is below the HOD by 37 points and below the 11:15 high of 27,149 by 30 points. The market could not reclaim the level that broke at 11:30.
- **12:30–12:55**: Four consecutive 5m bars unable to close above 27,101. Range compression inside a descending structure.

By 12:55 the consolidation had produced a lower high (27,118 < 27,156), a failed reclaim of D OPEN, and a descending internal sequence. The top was structurally confirmed.

### The Delivery (12:55–13:45)

- **12:55–13:00**: Open 27,088.25, high 27,098.75, **low 27,000.5**, close 27,013.75. Single 5m bar, 88-point range, 74-point body, 42,177 volume — the highest volume print of the afternoon. This is the breakdown bar.
- **13:00–13:05**: Low 26,950. Continuation. Below PWH 26,883? Not yet.
- **13:05–13:10**: Low 26,922.75. Below Midnight Open 26,908 on close.
- **13:10–13:15**: Low 26,865.5. Below PWH 26,883 on close.
- **13:15–13:35**: Stair-step down through 26,860–26,935 range.
- **13:35–13:40**: Low 26,847.5. New session low.
- **13:40–13:45**: **Low 26,744.5, then low 26,680**. Swept PDL by 48 points. Session bottom.

From the lower high at 27,118 to the low at 26,680: 438 points in 50 minutes. No reaction at D OPEN, Midnight Open, or PWH. A clean delivery.

---

## Part II — What Made the Top Callable in Advance

The top was not guessed. It was read. Five conditions were visible in real time before the 11:30 high printed.

### 1. The Liquidity Map Was Asymmetric

By 11:00 a.m., the upside contained exactly one untouched major reference: PDH 27,138. The intermediate cluster at 27,080 had already been traded through. Above PDH: open air until the next weekly reference far above.

The downside contained the session low at 26,744 area (not yet printed but implicit), PDL 26,728, and nothing else for 400+ points.

This is the **liquidity void** condition. When upside has one reference and downside has one reference, the market's job is to take both. Start with the nearer, deliver to the farther. A sweep of PDH, in that context, is not a continuation signal. It is the completion of the upside leg and the precondition for the reversal.

**Detection rule**: If the highest unused liquidity above price is a single named level (PDH, PWH, PMH, or a clear equal-highs pool) with no further reference for at least 100 points above, treat a sweep of that level as a reversal candidate, not a continuation.

### 2. The Price Was in Extreme Premium of the HTF Dealing Range

PDH is by definition the top of the prior session's range. A sweep of PDH places price in premium of the daily range, at the extreme edge. The 4H dealing range — from the April 22 low near 26,551 to the April 22 high at 27,138 — placed the 11:30 print at the 103% retracement. There is no more premium territory than that.

ICT reversal condition two requires the sweep to occur in premium for a short. The April 23 sweep was not merely in premium; it was at the boundary. Any price action above the dealing range must either continue displacing upward (a new leg, requiring volume expansion) or reverse. There is no middle state at the edge.

**Detection rule**: Draw the Fibonacci tool from the most recent HTF swing low to the HTF swing high that defines the dealing range. A sweep that prints at or above 100% of that range, with no continuation, is a reversal candidate. The deeper the sweep into extreme premium, the cleaner the reversal setup.

### 3. The Time Was Correct

The high printed at 11:25–11:30 a.m. ET. This sits inside the **London Close killzone** (10:00 a.m.–12:00 p.m.). The killzone's function is to reverse the move established during the NY AM killzone. When the NY AM move is a rally into overhead liquidity, the London Close killzone produces the top. This is not a tendency. It is the defining behavior of the window.

The Silver Bullet target filled at 11:19 added a second time component. The Silver Bullet (10:00–11:00) produced a long that ran into PDH. When institutional flow that took a long book off at the level is itself the fuel for the final squeeze above — traders who bought the Silver Bullet win are now flat; latecomers are still long and require the stop-hunt above for liquidity — the reversal is mechanically triggered by the exit of the winning cohort.

**Detection rule**: Rally reversals inside the London Close killzone carry weight the first hour of cash session reversals do not. If the NY AM killzone produced a displacement toward a single named liquidity pool, the London Close killzone reversal of that displacement is the expected outcome, not the exception.

### 4. The Sweep Was a Double-Tap on Declining Volume

Price printed 27,149.5 at 11:15–11:20, pulled back to 27,127, and printed 27,156 at 11:25–11:30. The final high was 6.5 points above the prior. A marginal new high on declining momentum.

Volume during the final push:

| Bar (ET) | Volume |
|----------|--------|
| 11:05–11:10 | 12,745 |
| 11:10–11:15 | 9,184 |
| 11:15–11:20 | 12,127 |
| 11:20–11:25 | 8,429 |
| 11:25–11:30 | 10,018 |

Compare to the 9:30–9:45 cash-open drive: 31,650 / 21,519 / 36,127. The final push to HOD occurred at 30–40% of cash-open volume. Institutional participation had already departed.

**Detection rule**: When the final impulse into a liquidity pool prints on volume less than half the volume of the session's prior impulse moves, treat the move as stop-hunt flow, not directional flow. Marginal new highs on declining volume are exhaustion, not strength.

### 5. The First Reversal Bar Was Structural, Not Cosmetic

The 11:30–11:35 bar opened at 27,146.25 and closed at 27,126.75 — a 19.5-point body, zero upper wick of consequence, and a close below the prior bar's low (27,119.25 from the 11:25 bar). This is displacement in the opposite direction immediately after the HOD.

ICT reversal condition three requires CHoCH driven by displacement. On the 1m chart, the CHoCH printed inside the 11:30 bar. On the 5m, the CHoCH became structural when the 11:35–11:45 sequence confirmed lower-high / lower-low behavior with no retracement wick back to the 27,146 level.

**Detection rule**: A valid reversal reversal bar at the HOD must close below the prior bar's low and produce an immediate second bar that does not reclaim the reversal bar's high. A reversal bar that closes strongly but is immediately reclaimed is not a reversal; it is a failed sweep of a different kind.

### The Stacked Read at 11:30

Before the 11:30–11:35 close printed, every condition above was already observable:

- PDH was swept twice.
- Price was above the dealing range.
- The NY AM killzone had already produced its move.
- Volume on the final push was weak.
- Upside held no further references.

The reversal bar was the confirmation, not the prediction. The prediction was the setup — a short thesis that existed the moment PDH was taken the second time.

---

## Part III — Mapping to the ICT Reversal Framework

The framework requires five conditions. All five were present on April 23. This is the grading:

| Condition | Required | Observed | Grade |
|-----------|----------|----------|-------|
| Liquidity Sweep | Wick through a named pool, close back inside within 3 bars | PDH 27,138 taken to 27,142.5 at 11:15, HH to 27,156 at 11:30, close back below 27,138 by 11:30–11:35 | A |
| PD Array Location | Sweep in extreme premium for shorts | Sweep at 103% of the 4H dealing range. Maximum premium. | A |
| Structural Shift | CHoCH on the execution timeframe post-sweep, driven by displacement | 1m CHoCH during 11:30 bar, 5m CHoCH when 27,061 broke at 12:55 | A |
| Entry Model | FVG or OB inside the reversal displacement | Bearish FVG formed 11:30–11:45 between 27,120 and 27,146 | A |
| Time Gate | Sequence inside a killzone | London Close killzone (10:00–12:00). NY AM just closed. | A |

A 5/5 setup. Every condition met in full. This is the highest-quality reversal setup the framework produces.

The entry, taken by the framework's rules:

- **Entry**: Retest of the 11:30–11:45 bearish FVG. The gap was 27,120 to 27,146. Price retested to 27,118.75 at 12:25–12:30 and rejected. This was the short trigger.
- **Stop**: Above HOD 27,156 with a 5-point buffer — 27,161.
- **Target 1**: D OPEN 27,080.75 (broken by 11:45).
- **Target 2**: PWH 26,883.
- **Target 3**: PDL 26,728.

Risk from 27,118 entry to 27,161 stop: 43 points. Reward to PDL: 390 points. R-multiple: 9.07. The setup grades A on both the framework and on R:R.

---

## Part IV — The Delivery vs. Consolidation Read

The user's central question: how did you know price would deliver to PDL rather than consolidate for the afternoon?

The answer lives in the 11:45–12:55 consolidation window. Every tape produces this decision phase after a failed high. The read is not a feel; it is a sequence.

### The Four Tells That Signaled Delivery

#### Tell 1 — The Failed Reclaim

After the 11:30–11:45 reversal leg, price rallied into 27,082 at 12:05–12:10. This was the first test of D OPEN from below. A clean reclaim — close above 27,080.75 that sustained for two bars or more — would have opened the door back to the 11:30 high. Price printed 27,082.75 and failed. The next close was 27,050.

Reclaim failures at a recently broken key level are the single most reliable signal that the break is structural. D OPEN was the line in the sand. Price could not cross back.

**Detection rule**: After an initial reversal, the first rally back to the most recently broken key level is the verdict. Reclaimed and held → the reversal has failed. Rejected → the reversal is structural and a delivery is in progress.

#### Tell 2 — The Lower High at 27,118

At 12:25–12:30, price rallied to 27,118.75. This was 37 points below the HOD and 30 points below the 11:20 high of 27,149. The print constructed a descending sequence: 27,156 → 27,149 → 27,118. Three successively lower highs across 60 minutes.

A true consolidation produces overlapping highs inside a horizontal box. The April 23 window produced descending highs inside a downward-sloped channel. The distinction is structural and definitive.

**Detection rule**: Use the 6-bar overlap ratio (from the ICC framework) during the decision window. Ratio < 0.35 with descending internal highs is not consolidation — it is a distribution phase. Distribution precedes delivery.

#### Tell 3 — Volume Compression at the Lower High

The 12:25–12:30 lower high printed on 12,509 volume. Compare to the 11:10–11:15 first sweep of PDH at 9,184 and the 11:25–11:30 HOD at 10,018. The retest volume was similar in magnitude but directionally impotent — high volume with no follow-through means absorption. Institutions sold into the rally.

**Detection rule**: A rally into the broken level that prints on volume ≥ the volume at the original sweep but fails to close above is distribution. The absorbed volume is the sellers' fill.

#### Tell 4 — The Expanding Downside Range

During the consolidation, each downside leg reached progressively deeper:

- First down-leg: 27,156 → 27,061 (95 points).
- Second down-leg (from 27,118 LH): 27,118 → 27,044 (74 points).
- Breakdown leg: 27,088 → 27,000 (88 points in one bar).

The downside bars were larger than the upside bars throughout the window. Directional asymmetry inside a "range" is not a range. It is a distribution that looks like a range until the final drop.

**Detection rule**: Measure the average body size of the up-bars vs. the down-bars during the decision window. If down-bars exceed up-bars by 1.5× or more, the window is distributive, not balanced. Distribution resolves downward.

### The Four Tells That Would Have Signaled Consolidation

For completeness — had the move been a range day rather than a delivery:

1. **Price would have reclaimed D OPEN** on the first test, with a close above 27,080.75 that held for two or more bars.
2. **The retest high would have matched or exceeded 27,156**, with price re-entering the PDH level from above.
3. **Volume on the upside bars would have matched volume on the downside bars** — balanced distribution.
4. **The range would have compressed over time** rather than expanded. Lower highs AND higher lows, converging toward equilibrium.

None of these occurred on April 23. Every signal pointed to delivery.

### The Breakdown Trigger

At 12:50, price closed at 27,094. At 12:55, the 12:55–13:00 bar opened at 27,088 and carried to 27,000.5. The breakdown was the break of the 11:45 swing low at 27,044 on expanding volume (42,177).

The delivery-vs-consolidation decision was made structurally by the 12:25 lower high. The breakdown bar was the confirmation that the decision had been made correctly.

**Detection rule**: When a distribution phase ends with a break below the phase's low on volume at least 2× the phase's average, the delivery is active. Positions entered against the break will be run over by institutional flow; the market's job at that point is to reach the next major liquidity pool with no meaningful reaction.

---

## Part V — The Top-Tick / Bottom-Tick Framework

The conditions above generalize. What follows is the framework distilled into a usable system.

### The Seven Conditions for a Session-Extreme Reversal

A valid top-tick or bottom-tick setup requires all seven. Fewer is not a setup. The conditions fall in two groups: **Setup Conditions** (observable before the sweep) and **Confirmation Conditions** (observable after the sweep).

**Setup Conditions — observable before the sweep**

1. **Liquidity Asymmetry** — The near-side liquidity consists of a single dominant pool (PDH, PWH, PMH, or equal highs/lows) with no further reference of equal or greater priority for at least 100 points beyond. The far side contains at least one major liquidity pool within reach of a full delivery leg.

2. **HTF Range Position** — Price, at the moment of the sweep, is at or beyond the 100% boundary of the HTF dealing range. The sweep must land in extreme premium (for tops) or extreme discount (for bottoms). Intermediate sweeps do not qualify.

3. **Time Gate** — The sweep occurs inside a reversal-biased killzone: London Close (10:00–12:00) for NY AM reversals, NY PM (13:30–16:00) for intraday reversals of a morning low, London Open for Asian range extremes. NY AM itself can produce reversals but only when HTF context is already primed.

**Confirmation Conditions — observable after the sweep**

4. **Double-Tap or Marginal New Extreme** — Price either prints a double sweep (two highs within 5–10 points of each other) or a marginal new extreme (less than 10 points above the prior high on the session). Large new highs with expanding volume are continuation; tight new highs on declining volume are exhaustion.

5. **Volume Declension** — The final push into the extreme prints on volume less than 50% of the session's dominant impulse volume. Weak volume at the extreme means the institutional book is closed.

6. **Structural Reversal Bar** — Immediately after the extreme, a bar prints that (a) closes below the prior bar's low (for tops) or above the prior bar's high (for bottoms), and (b) is not reclaimed in the next bar. The reversal bar is a displacement bar, not a doji.

7. **Broken-Level Reclaim Failure** — Within the first 60 minutes after the reversal, price rallies back to the most recently broken intermediate level (D OPEN, a prior session pivot, or the breakout point into the extreme) and fails to reclaim it. This is the structural verdict.

### Grading

| Score | Interpretation | Action |
|-------|---------------|--------|
| 7/7 | Top-tick / bottom-tick A+ | Full size. Target is the opposing major pool. |
| 6/7 | Reversal with one weak condition | Reduced size. Verify which condition is weak and why. |
| 5/7 | Reversal-leaning setup; likely consolidation if conditions do not complete | Watch. Wait for the 7th condition to confirm or fail. |
| ≤ 4/7 | Not a reversal. Either continuation or range. | Skip. |

### The Delivery Decision (Post-Reversal)

After a valid reversal is confirmed, the question becomes whether the move delivers to the opposing pool or consolidates. The four tells:

1. **Reclaim Test**: Price rallies (for tops) or dips (for bottoms) to the most recently broken key level. Rejected → delivery is live. Reclaimed → reversal has failed.
2. **Descending/Ascending Highs or Lows**: The decision phase produces lower highs (after tops) or higher lows (after bottoms) in sequence. Three or more within 60 minutes is structural confirmation.
3. **Volume Absorption**: High volume rallies (or dips) that fail to close beyond the broken level indicate distribution, not consolidation.
4. **Asymmetric Bar Bodies**: Down-bars (after tops) or up-bars (after bottoms) average 1.5× or more the size of the opposing bars during the decision phase.

If all four tells are present → delivery to the opposing pool is the base case.
If fewer than three tells are present → consolidation is the base case; wait for the decision window to resolve before re-engaging.

### Entry Mechanics

**For a top-tick short:**

- **Entry**: On the retest of the reversal FVG or the broken intermediate level (whichever price hits first). This is the lower high inside the decision window.
- **Stop**: Above the session extreme with a 3–5 point buffer on MNQ, 10–20 on ES, 1–2 points on gold.
- **Target 1**: The broken intermediate level (D OPEN, Midnight Open, or the next major reference below).
- **Target 2**: PWH if applicable.
- **Target 3**: PDL — the full delivery target.

**For a bottom-tick long:**

Inverse of the above. Entry on retest of the reversal bullish FVG or broken intermediate level, stop below the session extreme, targets PDH or PWL depending on context.

### Invalidation

The trade is out under any of the following:

1. Price reclaims the session extreme after entry. The reversal thesis is void.
2. The reclaim test succeeds — price closes above the broken level (for shorts) or below it (for longs) and holds for two or more bars.
3. Volume on the expected delivery leg is less than the consolidation volume. A drift with no expansion is not a delivery.
4. The decision window extends beyond 90 minutes without producing either delivery or a clean reclaim. Time stop.

---

## Part VI — Application Checklist

The checklist is skill-readable. Each item is a binary condition.

**Setup phase (pre-sweep):**

- [ ] **Single dominant near-side pool identified** — exactly one major reference with no further reference within 100 points beyond.
- [ ] **Far-side pool within delivery range** — at least one major reference in the opposite direction within 300–500 points.
- [ ] **Price at or beyond 100% of HTF dealing range** — in extreme premium (short) or extreme discount (long).
- [ ] **Reversal-biased killzone active or about to open** — London Close for NY AM reversals; NY PM for morning-low reversals; London Open for Asian extremes.

**Sweep phase:**

- [ ] **Sweep occurred** — wick through the pool, close back inside within 3 bars.
- [ ] **Double-tap or marginal new extreme** — second high within 10 points of first, or new extreme less than 10 points above prior.
- [ ] **Volume declined** — final push on volume < 50% of the session's dominant impulse bar volume.
- [ ] **Structural reversal bar** — displacement bar in opposite direction, closes beyond prior bar's high/low, not reclaimed next bar.

**Decision phase (post-reversal, first 60 minutes):**

- [ ] **Reclaim test failed** — rally or dip to broken intermediate level rejected.
- [ ] **Descending/ascending sequence formed** — three or more progressively lower highs (top) or higher lows (bottom).
- [ ] **Volume absorption visible** — high-volume counter-rally prints closed short of the broken level.
- [ ] **Asymmetric bar bodies** — delivery-direction bars larger than opposing bars by 1.5× or more.

**Execution:**

- [ ] **Entry at retest of reversal FVG or broken level** — not at the extreme.
- [ ] **Stop beyond session extreme** with instrument-appropriate buffer.
- [ ] **Targets defined in tiers** — broken level, next major reference, opposing pool.
- [ ] **R:R ≥ 3:1 to the opposing pool** — if not, skip or reduce to tactical target only.

If any setup-phase or sweep-phase item is unchecked, the reversal thesis is not live. If the decision phase fails to complete within 90 minutes, the trade is invalidated by time stop.

---

## Part VII — What This Framework Is Not

This framework does not predict every reversal. The majority of session extremes will form without all seven conditions aligning. A top on a sweep in the middle of the dealing range, outside a killzone, on normal volume is not a top-tick setup. It is noise.

This framework does not guarantee delivery. A 7/7 reversal setup that produces only a 30% delivery is a valid outcome; the framework only commits that the reversal itself is structural. Whether the delivery reaches the full opposing pool depends on the decision phase, and the decision phase can produce consolidation even after a 7/7 reversal.

The April 23 MNQ setup was a 7/7 with a 4/4 delivery phase. All conditions hit. The move ran from 27,156 to 26,680 — a 476-point session reversal with a clean sweep of PDL. The framework exists to identify this class of setup before it completes.

The honest summary: session-extreme reversals look perfect because the conditions that produce them are narrow. The edge is in recognizing the narrow set and waiting for it. Everything else is variance.

---

## Appendix — April 23 MNQ Numbers

| Event | Time (ET) | Price |
|-------|-----------|-------|
| Session open | 09:30 | 27,004 |
| Cash open high | 09:40 | 27,102.5 |
| Morning low | 09:55 | 26,966 |
| Silver Bullet entry | 10:31 | 27,036.5 |
| First PDH sweep | 11:10–11:15 | 27,142.5 |
| Silver Bullet target | 11:19 | 27,139.5 |
| High of day | 11:25–11:30 | **27,156** |
| Reversal bar close | 11:30–11:35 | 27,126.75 |
| First leg low | 11:55 | 27,044.25 |
| Decision-phase LH | 12:25–12:30 | **27,118.75** |
| Breakdown bar | 12:55–13:00 | O 27,088.25 / L 27,000.5 |
| PDL sweep | 13:40–13:45 | 26,680 |
| Session low | 13:45 | **26,680** |
| PDL reference | — | 26,728 |
| Total session reversal | — | **476 points** |
