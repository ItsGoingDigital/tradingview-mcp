# ICT Reversals — Top and Bottom Ticking Framework

**A sub-strategy of the ICT methodology dedicated to identifying high-probability turning points**

---

## Preface

This framework exists for one purpose: to identify the specific price levels and conditions under which a directional move is likely to terminate and reverse. It is not a system for catching every top or bottom. It is a system for ignoring ninety percent of market movement and engaging only when five independent conditions stack in the same place at the same time.

The central claim is narrow. ICT reversal setups do not predict extremes. They locate them after the fact — within a small enough window that entry, stop, and target can be defined with precision. The "bottom tick" is not a forecast. It is the mechanical outcome of price completing a specific sequence: liquidity taken, discount reached, structure shifted, entry model offered, inside a liquidity window. When the sequence is present, the reversal has already happened. The entry is a reaction, not a prediction.

Everything below flows from that premise.

---

## The Five Conditions

A valid reversal setup requires all five of the following. Fewer than five is not a setup. It is a watch.

1. **Liquidity Sweep** — Price has taken out a pool of resting orders at an obvious swing high or swing low.
2. **PD Array Location** — The sweep occurred in the premium zone (for shorts) or discount zone (for longs) of the relevant dealing range.
3. **Structural Shift** — After the sweep, price has broken the nearest opposing swing on a lower timeframe (MSS/CHoCH).
4. **Entry Model** — A Fair Value Gap, Order Block, or Breaker Block has been created inside the structural shift and is available for retracement entry.
5. **Time Gate** — The sequence occurred inside a killzone (London, New York AM, or New York PM).

Each condition is defined below with explicit detection rules.

---

## Condition 1: Liquidity Sweep

### Definition

A **liquidity sweep** is a price action event in which the market trades through an obvious swing high or swing low, triggers the resting stop orders at that level, and then reverses. The sweep is the mechanical consumption of those stops — the fuel institutions require to fill size on the opposite side.

### What qualifies

- **Buy-side liquidity (BSL)** sits above swing highs, equal highs, and obvious session highs (PDH, PWH, Asian high, prior balance high).
- **Sell-side liquidity (SSL)** sits below swing lows, equal lows, and obvious session lows (PDL, PWL, Asian low, prior balance low).
- The sweep requires a **wick through** the level — the high (or low) of the bar exceeds the reference level, but the close does not sustain beyond it.

### Detection rules

A sweep is valid when all of the following are true:

- A prior swing high or swing low has been marked as a reference level before the event occurs.
- Price prints a high (for a BSL sweep) or low (for an SSL sweep) that exceeds the reference level by at least one tick.
- Within three bars of the extreme, price closes back inside the reference level (below the swept high; above the swept low).
- The bar that printed the extreme is not followed by additional continuation bars in the same direction — the move stalls or reverses immediately.

### What disqualifies

- A **clean break** — close beyond the level with follow-through. This is a BOS, not a sweep. It is a continuation, not a reversal setup.
- A sweep of **unqualified liquidity** — wicks through random intraday fractals with no prior significance. The sweep must target a level that was marked as a reference before the event.
- A sweep during low-liquidity hours (outside killzones) with no follow-up structural confirmation.

### Priority of liquidity pools

Not all pools are equal. In descending order of significance:

1. Previous Month High/Low (PMH/PML)
2. Previous Week High/Low (PWH/PWL)
3. Previous Day High/Low (PDH/PDL)
4. Asian session high/low
5. Equal highs/equal lows (double tops/bottoms forming horizontal liquidity)
6. Intraday session highs/lows

Sweeps of higher-priority levels produce larger reversals. A setup that sweeps PWH has more weight than one that sweeps an intraday equal high.

---

## Condition 2: PD Array Location

### Definition

The **dealing range** is the span between the most recent significant swing high and the most recent significant swing low on the timeframe being analyzed. The midpoint of that range is **equilibrium**. Above equilibrium is **premium**. Below equilibrium is **discount**.

Longs are sought in discount. Shorts are sought in premium. Reversals that occur against this rule are counter-trend and carry reduced probability.

### Detection rules

For a **long reversal** (bottom tick):

- Identify the current dealing range: the most recent higher high to the most recent higher low on the HTF (4H or Daily).
- Apply a Fibonacci tool from the range high to the range low.
- The liquidity sweep (Condition 1) must occur **below the 50% retracement** — inside discount.
- Optimal Trade Entry (OTE) zone: 62% to 79% retracement. Sweeps that land inside OTE carry the highest probability.

For a **short reversal** (top tick):

- Identify the dealing range: the most recent lower low to the most recent lower high.
- Apply the Fibonacci tool from the range low to the range high.
- The liquidity sweep must occur **above the 50% retracement** — inside premium.
- OTE zone: 62% to 79% retracement measured from low to high.

### What disqualifies

- A sweep in discount when the HTF bias is bearish (this is continuation territory, not reversal).
- A sweep in premium when the HTF bias is bullish (same reason, opposite direction).
- A sweep that lands outside OTE (below 62% or above 79% of the retracement measured correctly).

PD Array location is the single most common filter for separating tradeable reversal setups from noise. Sweeps that occur in the wrong zone are traps.

---

## Condition 3: Structural Shift (MSS / CHoCH)

### Definition

A **Change of Character (CHoCH)** is the first break of the prevailing lower-timeframe structure in the direction of the intended reversal. In a downtrend approaching a bottom, CHoCH is the first break above a recent lower high after the sweep. In an uptrend approaching a top, CHoCH is the first break below a recent higher low after the sweep.

A **Market Structure Shift (MSS)** is CHoCH plus follow-through: price holds above the broken level (for a bullish MSS) or below the broken level (for a bearish MSS) and begins forming structure in the new direction.

The structural shift is what converts a sweep from "possible reversal" to "confirmed reversal." Without it, the sweep is unconfirmed.

### Detection rules

For a **bullish reversal** (after an SSL sweep):

- Identify the most recent swing high on the execution timeframe (typically 5m or 15m for intraday; 1H for swing). This is the CHoCH reference.
- CHoCH confirms when a candle closes above that swing high.
- MSS confirms when, after CHoCH, price pulls back without breaking below the sweep low and then makes a higher low.

For a **bearish reversal** (after a BSL sweep):

- Identify the most recent swing low on the execution timeframe.
- CHoCH confirms when a candle closes below that swing low.
- MSS confirms when, after CHoCH, price pulls back without breaking above the sweep high and then makes a lower high.

### Timeframe selection

- **4H/Daily swing reversals** → CHoCH on the 1H
- **Intraday reversals within a killzone** → CHoCH on the 5m or 15m
- **Scalp reversals** → CHoCH on the 1m

The execution timeframe must be at least two steps below the bias timeframe. Using the same timeframe for bias and CHoCH produces false signals.

### What disqualifies

- A CHoCH that occurs **before** the liquidity sweep. The sequence must be: sweep first, then CHoCH. A CHoCH without a preceding sweep is a continuation signal, not a reversal.
- A CHoCH that occurs with no displacement — a weak, slow break with overlapping candles and long wicks. Valid CHoCHs are driven by displacement bars.
- A "CHoCH" on a timeframe that is too high relative to the setup (e.g., 1H CHoCH for a 5m killzone trade). This is the wrong tool.

---

## Condition 4: Entry Model

### Definition

The entry model is the specific price zone where execution occurs. After CHoCH, price typically retraces before continuing in the new direction. The retracement zone is defined by one of three structures, listed in order of preference:

1. **Fair Value Gap (FVG)** — a three-candle imbalance created inside the displacement that produced CHoCH.
2. **Order Block (OB)** — the last opposing candle before the displacement began.
3. **Breaker Block** — a prior OB that has been violated and is now acting in the opposite direction.

### Detection rules — Fair Value Gap

A **bullish FVG** (for long entries):

- Three consecutive candles inside the displacement that produced CHoCH.
- The high of candle 1 is strictly lower than the low of candle 3.
- The gap = [high of candle 1, low of candle 3].
- Consequent Encroachment (CE) = midpoint of the gap.

A **bearish FVG** (for short entries):

- The low of candle 1 is strictly higher than the high of candle 3.
- The gap = [high of candle 3, low of candle 1].
- CE = midpoint.

### Detection rules — Order Block

A **bullish OB** (for long entries):

- The last bearish (red) candle before the displacement that produced CHoCH.
- Zone = [low, high] of that candle. Conservative variant: [open, close].

A **bearish OB** (for short entries):

- The last bullish (green) candle before the displacement that produced CHoCH.
- Zone = [open, close] or [low, high].

### Execution mechanics

- **Entry**: Limit order at the near edge of the FVG or OB. More aggressive: at CE of the FVG. More conservative: at the far edge.
- **Stop**: Beyond the liquidity sweep extreme. For a long, stop goes below the swept low. For a short, stop goes above the swept high.
- **Target**: The opposing liquidity pool. For a long off an SSL sweep, target the nearest BSL above. For a short off a BSL sweep, target the nearest SSL below.

### What disqualifies

- An FVG or OB that sits **outside the retracement zone** (price has already traded through it by the time CHoCH prints).
- An entry model that requires a stop **wider than the sweep wick**. If the structural stop is beyond where you need it, the setup is not clean — skip it.
- Relying on an OB when an FVG inside the same displacement offers tighter risk. The FVG takes precedence.

---

## Condition 5: Time Gate

### Definition

Institutional order flow is concentrated in specific windows. Reversals that occur inside those windows are driven by scheduled liquidity events. Reversals outside those windows are statistical noise unless a higher-timeframe level is in play.

### Killzones (New York time)

| Window | Time | Instrument Focus |
|--------|------|-----------------|
| London KZ | 2:00 AM – 5:00 AM | FX, gold, European indices |
| New York AM KZ | 7:00 AM – 10:00 AM | US indices, US equities, USD pairs |
| London Close KZ | 10:00 AM – 12:00 PM | Reversals of the NY AM move |
| New York PM KZ | 1:30 PM – 4:00 PM | Afternoon reversals, end-of-day liquidity |
| Asian KZ | 7:00 PM – 10:00 PM | AUD, JPY, Asian session ranges |

### Detection rules

- The **liquidity sweep** (Condition 1) must occur inside a killzone, OR within fifteen minutes of the killzone opening (pre-open sweeps are valid; they often set up the killzone move itself).
- The **CHoCH** (Condition 3) must occur inside the same or the immediately following killzone.
- The entry model (Condition 4) must be present by the time CHoCH prints. Setups that develop entirely outside killzones are downgraded.

### Instrument-specific killzone priority

- **MNQ / ES / NQ / US equities** → NY AM KZ is primary. London KZ is secondary (pre-positioning). NY PM KZ is tertiary (reversals of AM).
- **MGC / Gold / Silver** → London KZ is primary. Shanghai AM (21:00–22:00 ET) is a specialized window.
- **FX majors** → London KZ and London/NY overlap (8:00–10:00 ET) are primary.
- **CL / Crude** → NY AM KZ, particularly around the EIA release window on Wednesdays.

### What disqualifies

- A setup that completes entirely inside a dead zone (between killzones, overnight outside Asian KZ). Even with all four other conditions, the absence of institutional participation reduces the probability materially.
- A killzone setup during a low-volume day (major holiday, half-session, FOMC blackout). Time-of-day is not sufficient; day-type matters.

---

## Application Layer — Execution Sequence

The conditions above are detected in a strict order. Skipping steps or reordering produces false signals.

### Step 1: Higher-Timeframe Bias

Before any reversal setup is considered, establish HTF context.

- Daily structure: bullish (HH/HL), bearish (LH/LL), or ranging.
- 4H structure on the same instrument.
- Location of current price within the HTF dealing range: premium, discount, or equilibrium.

**Rule**: Counter-trend reversals (longs in a bearish HTF, shorts in a bullish HTF) are only taken when the sweep targets a higher-timeframe liquidity pool (PWH/PWL/PMH/PML). Reversals against HTF bias without HTF liquidity are skipped.

### Step 2: Identify Liquidity Targets

Mark the nearest untouched BSL and SSL pools on the HTF and the current session chart.

- PDH / PDL
- PWH / PWL (for futures, week begins Sunday 6:00 PM ET)
- PMH / PML
- Asian session high and low
- Obvious equal highs / equal lows inside the current session

These are the only levels that qualify as sweep targets. Random intraday wicks do not.

### Step 3: Monitor Killzone Approach

Wait for the killzone. Before the killzone opens:

- Confirm which liquidity pool is the most likely target (usually the one price is approaching or has recently left).
- Confirm whether that pool sits in HTF discount (long setup) or HTF premium (short setup).
- If the pool is on the wrong side of HTF bias — skip the session.

### Step 4: Wait for the Sweep

Inside the killzone, or within fifteen minutes of its open:

- Watch for price to wick through the targeted liquidity pool.
- Confirm the wick meets the detection rules in Condition 1 (exceeds level, closes back inside, does not continue).
- Mark the sweep extreme — this becomes the stop reference.

### Step 5: Wait for CHoCH

After the sweep:

- Identify the nearest opposing swing on the execution timeframe (5m or 15m).
- Wait for a close beyond it.
- Confirm the break is driven by displacement — large-bodied bars, minimal opposing wicks.

If CHoCH does not occur within the current killzone, the setup is dead. Reversals require timely structural confirmation. A "delayed CHoCH" that prints two hours after the sweep is a different setup (and usually a worse one).

### Step 6: Identify the Entry Model

Inside the displacement that produced CHoCH:

- Scan for a Fair Value Gap. Mark it. This is first preference.
- If no FVG, identify the Order Block (last opposing candle before the displacement).
- The entry model must sit inside the retracement zone — somewhere between the sweep extreme and the CHoCH break point.

### Step 7: Place the Trade

- **Entry**: Limit order at the near edge (or CE) of the entry model.
- **Stop**: Beyond the sweep extreme, plus a small buffer (typically 2–5 ticks on futures, depending on instrument volatility).
- **Target 1**: Nearest opposing liquidity pool.
- **Target 2**: The next PD Array on the HTF (previous session high/low, HTF FVG).

### Step 8: Manage or Skip

- If price trades to the entry model and holds → the trade is active. Manage to target.
- If price trades to the entry model and breaks through without reaction → the setup has failed. Exit at stop.
- If price never trades to the entry model (walks away in the intended direction) → missed. Do not chase.

---

## Confluence Scoring

Not every setup has all five conditions at equal strength. Score each setup 0–5 based on how many conditions are met in full. Partial conditions do not count.

| Score | Interpretation | Action |
|-------|---------------|--------|
| 5/5 | All conditions met, HTF bias aligned | Full size |
| 4/5 | One condition weak (typically time or HTF alignment) | Reduced size |
| 3/5 | Multiple weak conditions | Paper trade or skip |
| ≤ 2/5 | Not a setup | Skip |

The common failure modes for 4/5 setups:

- Sweep occurred before the killzone opened, no follow-up sweep inside (time gate weak).
- HTF bias is ranging rather than cleanly trending (bias alignment weak).
- Entry model requires a wider-than-ideal stop (entry model weak).

A 5/5 setup on a major HTF liquidity pool inside the primary killzone is the highest-quality reversal available. It is also rare — typically one or two per week per instrument. The framework is designed to wait for these.

---

## Invalidation Conditions

A reversal setup is invalidated — exited at market or at stop — under the following conditions:

1. **Stop hit**: Price trades beyond the sweep extreme plus buffer.
2. **Displacement failure post-entry**: After entry, the next three bars do not show displacement in the trade direction. Exit at breakeven or small loss.
3. **Counter-CHoCH**: Price, after entry, breaks the CHoCH level in the opposite direction. The structural shift has been nullified.
4. **Time stop**: Setup does not reach target within the current killzone plus one hour. Positions held beyond this are exposed to session-end liquidity risk.
5. **Higher-timeframe invalidation**: The HTF structure that provided bias shifts during the trade. This is rare but definitive.

Invalidation is not a failure of the framework. It is the normal distribution of outcomes. The framework defines invalidation before entry so that losses are capped and pre-committed.

---

## What This Framework Is Not

This document does not claim to predict every reversal. The majority of intraday highs and lows will form without all five conditions aligning. Those moves are not targets. They are noise to be ignored.

This framework does not guarantee a winning trade. It defines a repeatable sequence with a positive expected value over a sufficient sample. Individual setups fail. The edge is in only trading setups that meet the criteria and in exiting quickly when they fail.

This framework is not a replacement for chart study. The detection rules are explicit but their application requires pattern recognition built from studying hundreds of historical examples. A skill executing this framework must be able to identify the relevant swing highs and lows, measure the dealing range correctly, and distinguish a sweep from a break. Those are judgments, not computations.

The honest summary: when the five conditions stack inside a single killzone at a high-priority liquidity level, the entry will often be within a small handful of ticks of the session extreme. That is not magic. It is the structural result of liquidity being taken, displacement occurring, and the market offering a retracement entry inside the imbalance. The "bottom tick" appearance is a by-product of the sequence, not its goal.

---

## Checklist — Pre-Entry

Before any reversal trade is placed, all items below must be checked:

- [ ] **HTF bias identified** — Daily and 4H structure classified
- [ ] **Liquidity pool marked** — Specific named level (PDH, PWL, Asian high, etc.)
- [ ] **PD Array location confirmed** — Sweep occurred in correct zone (discount for longs, premium for shorts)
- [ ] **Sweep validated** — Wick through level, close back inside, no continuation
- [ ] **CHoCH confirmed** — Close beyond nearest opposing swing on execution timeframe
- [ ] **Displacement present** — Structural break driven by large-bodied bars, not overlapping chop
- [ ] **Entry model identified** — FVG (preferred) or OB inside the CHoCH displacement
- [ ] **Time gate open** — Sequence completed inside an active killzone
- [ ] **Stop location acceptable** — Risk to sweep extreme is proportional to target distance (minimum 2:1)
- [ ] **HTF alignment** — Trade direction matches HTF bias, or targets HTF liquidity when counter-trend

If any item is unchecked, the setup is not live. Wait or skip.

---

## Rules

- Never enter before the sweep. The sweep is the first condition, not the third.
- Never enter before CHoCH. Counter-trend entries without structural confirmation are guesses.
- Never enter outside a killzone unless the setup targets a major HTF liquidity pool (PWH/PWL/PMH/PML).
- Never widen a stop. The stop is defined by the sweep extreme. If that stop is too wide for acceptable R:R, the setup is skipped, not adjusted.
- Never chase a missed entry. If price leaves the entry model without trading into it, the trade is gone.
- Never take two reversals in the same direction within the same killzone. The first one either worked or failed — doubling down is revenge trading.
- PD Array alignment is mandatory. Longs in premium and shorts in discount are forbidden regardless of other confluence.
- FVG takes precedence over OB when both exist in the same displacement.
- Target the opposing liquidity pool. Not a random round number, not an indicator level — the opposing BSL or SSL.
- Time-stop any trade that has not reached first target within the current killzone plus one hour.
