# ICC Trading Strategy

**Indication, Correction, Continuation**

A multi-timeframe trend continuation framework. The 4H chart establishes directional bias and identifies the indication. The 15m (or 5m) chart times entries during pullbacks.

---

## Phase Definitions

**Indication** — Price breaks a prior pivot high or pivot low on the 4H, creating new structure. The broken level is the indication price.

**Correction** — Price retraces against the indication direction. The 15m will trend counter to the 4H bias (LH/LL during a bullish correction, HH/HL during a bearish correction).

**Continuation** — The 15m reverses back in the indication direction. This is the only phase where entries are taken.

---

## Analysis Workflow

### 1. Establish 4H Trend

Use **pivot highs and lows** — the major turning points visible when you zoom out. A pivot has clear price action building into it and clear price action moving away from it (multiple bars on each side). Ignore minor swing points within a move; those are micro-structure for the 15m, not the 4H.

| Structure | Trend | Action |
|-----------|-------|--------|
| Higher pivot highs + higher pivot lows | Bullish | Look for longs |
| Lower pivot highs + lower pivot lows | Bearish | Look for shorts |
| No clear structure | Choppy | **No trade** |

If the 4H is chopping, stop. No lower timeframe signal overrides this.

### 2. Identify the Indication Price

The indication price is the **pivot level that was broken** — not the resulting new high or low.

- **Bullish**: The prior pivot high that price broke above
- **Bearish**: The prior pivot low that price broke below

The new high or low that results from the break is the **take profit target**.

### 3. Determine Current Phase

Work through these **in order** — stop at the first match:

**A. Is price above/below the indication level?**
- If price has already reclaimed the indication level AND the 15m confirms structure in the indication direction → **Continuation**. Go to Step 4.
- If not, continue to B.

**B. Has price pulled back from the indication extreme?**
- If price is retracing against the indication direction AND the 15m is trending counter to the 4H bias (LH/LL during bullish, HH/HL during bearish) → **Correction**. Produce the Correction Levels Addendum (see below). Do NOT enter.
- If no pullback has started → **Still in Indication**. Watch, don't chase.

**C. Did the correction break the pivot HL/LH?**
- If the correction violated the 4H pivot HL (bullish) or pivot LH (bearish) → **Choppy / No Trade**. The trend structure is broken.

### 4. Entry & Trade Plan (Continuation phase only)

**Confirmation:** Price must have reclaimed the indication level. This confirms continuation — it is not the entry itself.

**Entry:** On the **next 15m pullback** within the continuation. Use correction levels, fib retracements, and PD array confluence to identify where the pullback may find support (bullish) or resistance (bearish). Enter at or near those levels.

**Take Profit:** The resulting new high/low from the indication move — the extreme that was created when price broke the indication level.

**Stop Loss:** Placed at the **break of 15m micro-structure** — the most recent 15m pivot HL (bullish) or pivot LH (bearish). This is tighter than the 4H invalidation and gives better R:R.

**Invalidation:** The 4H pivot HL (bullish) or pivot LH (bearish) that defines the trend. This is NOT the stop loss — it's the level where the entire thesis dies. If the 15m SL gets hit, re-evaluate: the thesis may still be alive if the 4H invalidation holds. Look for the 15m to re-establish continuation structure before re-entering.

| Level | Purpose |
|-------|---------|
| Indication price | Confirmation — must be reclaimed before looking for entry |
| 15m pullback level | Entry — where you actually get in |
| 15m pivot HL/LH | Stop loss — where you get out if micro-structure breaks |
| TP (prior high/low) | Take profit — the resulting extreme from the indication |
| 4H pivot HL/LH | Invalidation — thesis is dead, do not re-enter |

---

## Status Report Template

When assessing any futures chart, produce the following:

```
ICC STATUS — [SYMBOL] [DATE]

4H Trend:      [Bullish / Bearish / Choppy]
4H Structure:  [Pivot sequence, e.g., "PHL 4,306 → PHH 4,825 → PHL 4,580"]

Indication:    [Bullish / Bearish] break of [PRICE]
Take Profit:   [Resulting new high or low from the indication move]
Invalidation:  [Pivot HL/LH that defines the trend]
ICT Alignment: ChoCh [PRICE] | BOS: [PRICES] | Indication aligns with BOS: [Yes/No]

Current Phase: [Indication / Correction / Continuation / No Trade (choppy)]

15m Structure: [Current pivot sequence on 15m]
15m Confirms:  [Yes/No — structure matches expected behavior for current phase]

Entry:         [Not yet / Confirmed (price reclaimed indication) / Waiting for 15m pullback]
```

**If phase = Correction**, the Correction Levels Addendum follows immediately (mandatory).

**If phase = Continuation**, include the trade plan:
```
Trade Plan:
  Confirmation: Price reclaimed [indication price] ✓
  Entry:        Next 15m pullback (targeting [level/zone])
  Stop Loss:    [15m pivot HL/LH — micro-structure break]
  Take Profit:  [Resulting high/low from indication move]
  Invalidation: [4H pivot HL/LH — thesis dies here]
  Risk:         [Entry - SL]
  R:R:          [TP distance / Risk distance]
```

### Correction Levels Addendum

**Automatically produced when the current phase is Correction.** This is not optional — if the phase is Correction, this addendum must follow the status report. Identifies potential reversal levels where the correction may end. Does not influence the ICC phase analysis — it is supplementary confluence for timing.

**Directional filter:**
- **Bullish correction** (price pulling back down) → only report levels **at or below** current price (looking for support)
- **Bearish correction** (price pulling back up) → only report levels **at or above** current price (looking for resistance)

Levels on the wrong side of price are continuation targets, not correction levels. Exclude them.

**Fibonacci retracement:**
Measured from the most recent 4H pivot low to the resulting high (bullish) or pivot high to the resulting low (bearish):
- **Bullish**: From the pivot HL to the new high
- **Bearish**: From the pivot LH to the new low

Standard levels: 0.236, 0.382, 0.500, 0.618, 0.786. Same directional filter applies.

**Prior week calculation:**
Futures weekly session starts **Sunday 6:00 PM ET** (22:00 UTC during EDT, 23:00 UTC during EST). Prior week = Sunday open to Friday close.

```
CORRECTION LEVELS — [SYMBOL] [DATE]
([Bullish/Bearish] bias — looking for [support/resistance])
PD Array window: 4H [pivot point] to current

Key Levels:                              PD Array Confluence:
  [LEVEL NAME]:   [PRICE] ([distance])   [TF] [Type] [range] ([touched/UNTOUCHED])
  ...                                    ...

Fib measured from: [pivot HL/LH] → [resulting high/low]
```

All levels filtered to the correct side of price. Note any alignment with BOS/ChoCh levels.

**PD Array scan methodology:**

The scan window is anchored to the ICC structure:
- **Start**: The 4H pivot low (bullish) or pivot high (bearish) that launched the indication move
- **End**: Current bar

Scan both **4H and 15m** bars within this window. Detect FVGs and OBs. Filter to only zones whose range overlaps a correction level (±10 pts for 4H, ±5 pts for 15m). No overlap = exclude.

For each matching zone, note:
- Timeframe (4H or 15m)
- Type (Bull/Bear FVG or OB)
- Price range
- Touched or **UNTOUCHED**

Group PD Arrays next to the key level they align with. Highlight clusters where multiple levels and untouched zones stack.

**Workflow:**
1. Calculate key levels (Midnight Open, PDH, PDL, PD 50%, PWH, PWL, PW 50%)
2. Calculate fib retracement from pivot HL/LH to indication extreme
3. Filter all levels to the correct side of price
4. Note any alignment with BOS/ChoCh levels
5. Scan PD Arrays on 4H and 15m within the indication window
6. Filter to zones overlapping a key level
7. Note touched/untouched status

---

## Checklist

- [ ] **4H trend is clear** — Pivot HH/HL or LH/LL. Not choppy.
- [ ] **Indication is marked** — Broken pivot level identified, not the resulting extreme
- [ ] **Phase determined in order** — Continuation first, then Correction, then Choppy
- [ ] **If Correction** — Correction Levels Addendum produced (mandatory)
- [ ] **If Continuation** — Trade plan produced with entry, TP, invalidation, R:R
- [ ] **15m confirms phase** — Structure aligns with expected behavior
- [ ] **Indication reclaimed** — Price has crossed back through indication level
- [ ] **Entry on pullback** — Enter on 15m pullback, not at indication price itself
- [ ] **SL at 15m structure** — Stop loss at 15m pivot HL/LH, not 4H invalidation

---

## ChoCh and BOS on the 4H

These ICT concepts map directly onto the ICC framework and help establish when a trend has begun (ChoCh) versus when it is continuing (BOS).

### Definitions

**ChoCh (Change of Character)** — The first structural break *against* the prior trend. It signals the old trend may be over.

**BOS (Break of Structure)** — A structural break *in the direction of* the current trend. It confirms the trend is continuing.

### Identifying ChoCh After a Reversal

When a trend reverses (e.g., downtrend bottoms and starts to rally), the ChoCh is the **first pivot high that gets broken after the reversal low**.

Key logic:

1. **The reference must exist before the break.** After a reversal low, price rallies and forms a pivot high, then pulls back. When price breaks above that pivot high, that is the ChoCh.

2. **Waterfall moves compress structure.** In a sharp selloff, the 4H may print sequential lower bars without clean pivot highs between them. The first pivot high that forms after the reversal low becomes the ChoCh level.

3. **ChoCh is the level that was broken, not the resulting high.** Same principle as ICC indication.

4. **BOS then confirms.** Each subsequent pivot high (bullish) or pivot low (bearish) that gets broken is a BOS.

### Relationship to ICC

- **ChoCh** establishes that a trend exists — precondition for running ICC
- **BOS** = ICC **indication** — a broken pivot level confirming directional intent
- The most recent BOS on the 4H = the ICC indication price

---

## Rules

- Never enter during Indication or Correction — only Continuation
- Never trade a choppy 4H — no exceptions
- The indication price is the breakout level, not the new high/low
- The new high/low is the take profit target
- A correction that violates the 4H pivot HL/LH invalidates the setup
- Indication reclaim confirms continuation — it is not the entry
- Enter on the 15m pullback within continuation, not at the indication price
- Stop loss at 15m micro-structure (pivot HL/LH), not the 4H invalidation
- If 15m SL gets hit, re-evaluate — thesis may survive if 4H invalidation holds
- Correction Levels Addendum is mandatory when phase = Correction
- 4H uses pivot HL/LH (major turns), not micro swings — micro-structure is for the 15m
