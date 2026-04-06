# ICC Trading Strategy

**Indication, Correction, Continuation**

---

## Foundation: Market Structure

Everything in this strategy is rooted in one principle:

**For price to be trending upward, it must make higher highs and higher lows. For price to be trending downward, it must make lower highs and lower lows.**

This is market structure. ICC is simply a framework for identifying where we are within that structure and when to enter.

- A **higher high** = the market is indicating bullish intent. That's the **Indication**.
- The pullback that follows = the market forming the next higher low. That's the **Correction**.
- When the higher low holds and price resumes making higher highs = **Continuation**. This is where we trade.
- If the previous higher low breaks = the pattern of HH/HL is broken. The trend is over. That's **Invalidation**.

Every concept below — indication, correction, continuation, invalidation, fibs, correction levels — maps directly back to this structure. If you understand HH/HL and LH/LL, you understand ICC.

---

## Phase Definitions

**Indication** — Price makes a new higher high (bullish) or lower low (bearish) on the 4H by breaking the previous pivot high or pivot low. The broken level is the indication price. The resulting new extreme is the take profit target.

**Correction** — The retracement leg that forms the next higher low (bullish) or lower high (bearish). This is a **phase**, not a specific price level. ICC expects the correction to retrace **significantly past the indication level** — often deep into the leg that created the move. This is normal. We do not know where the correction will end — that is why we use fibonacci retracements, key levels, and PD array confluence to estimate where price may find support (bullish) or resistance (bearish) and reverse. The 15m will trend counter to the 4H bias during this phase.

**Continuation** — The correction holds (the higher low or lower high is established) and the 15m reverses back in the indication direction. Price resumes making HH/HL (bullish) or LH/LL (bearish). This is the only phase where entries are taken.

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

The indication is the most recent **higher high** (bullish) or **lower low** (bearish). Two components:

- **Indication price**: The previous pivot high/low that was **broken** to create the new extreme
- **Take profit**: The resulting new high/low — the extreme itself

### 3. Determine Current Phase

Work through these **in order** — stop at the first match:

**A. Is price above/below the indication level?**
- If price has already reclaimed the indication level AND the 15m confirms structure in the indication direction → **Continuation**. Go to Step 4.
- If not, continue to B.

**B. Has price pulled back from the new extreme?**
- If price is retracing against the indication direction AND the 15m is trending counter to the 4H bias → **Correction**. Price is forming the next HL (bullish) or LH (bearish). Produce the Correction Levels Addendum (see below). Do NOT enter.
- If no pullback has started → **Still in Indication**. Watch, don't chase.

### 4. Entry & Trade Plan (Continuation phase only)

**Confirmation:** Price must have reclaimed the indication level. This confirms the correction held and the trend is resuming — it is not the entry itself.

**Entry:** On the **next 15m pullback** within the continuation. Use correction levels, fib retracements, and PD array confluence to identify where the pullback may find support (bullish) or resistance (bearish). Enter at or near those levels.

**Take Profit:** The new high/low — the extreme that was created when price broke the indication level.

**Stop Loss:** Placed at the **break of 15m micro-structure** — the most recent 15m pivot HL (bullish) or pivot LH (bearish). This is tighter than the 4H invalidation and gives better R:R.

**Invalidation:** The **previous** 4H higher low (bullish) or lower high (bearish) — one pivot back from the most recent. If this level breaks, the pattern of HH/HL or LH/LL is broken and the trend is over. This is NOT the stop loss — it's where the thesis dies.

| Level | Market Structure Meaning |
|-------|--------------------------|
| Indication price | The previous HH/LL that was broken — confirms trend is making new structure |
| TP | The resulting new HH/LL — the extreme from the indication break |
| Most recent PHL/PLH | The correction low/high — the HL/LH being formed right now |
| Previous PHL/PLH | Invalidation — if this breaks, HH/HL or LH/LL pattern is broken |
| 15m pivot HL/LH | Stop loss — micro-structure break on the execution timeframe |
| 15m pullback level | Entry — where you actually get in |

---

## Status Report Template

When assessing any futures chart, produce the following:

```
ICC STATUS — [SYMBOL] [DATE]

4H Trend:      [Bullish / Bearish / Choppy]
4H Structure:  [Pivot sequence, e.g., "PHL 4,306 → PHH 4,825 → PHL 4,580"]

Indication:    [Bullish / Bearish] break of [PRICE]
Take Profit:   [Resulting new high or low]
Invalidation:  [Previous PHL/PLH — one pivot back from the most recent]
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
  Invalidation: [Previous 4H PHL/PLH — trend structure breaks here]
  Risk:         [Entry - SL]
  R:R:          [TP distance / Risk distance]
```

### Correction Levels Addendum

**Automatically produced when the current phase is Correction.** This is not optional — if the phase is Correction, this addendum must follow the status report. Identifies potential reversal levels where the next higher low (bullish) or lower high (bearish) may form. Does not influence the ICC phase analysis — it is supplementary confluence for timing.

**Directional filter:**
- **Bullish correction** (price forming the next HL) → only report levels **at or below** current price (looking for support)
- **Bearish correction** (price forming the next LH) → only report levels **at or above** current price (looking for resistance)

Levels on the wrong side of price are continuation targets, not correction levels. Exclude them.

**Fibonacci retracement:**
Measured across the **entire leg** that created the indication move. This covers the full range because ICC expects corrections to retrace significantly past the indication, deep into the leg.

- **Bullish**: From the bottom of the move (the higher low that launched the rally) to the top (the new higher high / TP)
- **Bearish**: From the top of the move (the lower high that launched the selloff) to the bottom (the new lower low / TP)

Standard levels: 0.236, 0.382, 0.500, 0.618, 0.786. Same directional filter applies — only report fibs on the correct side of price.

**Prior week calculation:**
Futures weekly session starts **Sunday 6:00 PM ET** (22:00 UTC during EDT, 23:00 UTC during EST). Prior week = Sunday open to Friday close.

```
CORRECTION LEVELS — [SYMBOL] [DATE]
([Bullish/Bearish] bias — looking for [support/resistance])
PD Array window: 4H [pivot point] to current

Key Levels:                              PD Array Confluence:
  [LEVEL NAME]:   [PRICE] ([distance])   [TF] [Type] [range] ([touched/UNTOUCHED])
  ...                                    ...

Fib measured from: [HL that launched the move] → [new HH] (bullish)
```

All levels filtered to the correct side of price. Note any alignment with BOS/ChoCh levels.

**PD Array scan methodology:**

The scan window is anchored to the ICC structure:
- **Start**: The 4H higher low (bullish) or lower high (bearish) that launched the indication move
- **End**: Current bar

Scan both **4H and 15m** bars within this window. Detect FVGs and OBs. Filter to only zones whose range overlaps a correction level (within **±0.2% of current price**). No overlap = exclude.

For each matching zone, note:
- Timeframe (4H or 15m)
- Type (Bull/Bear FVG or OB)
- Price range
- Touched or **UNTOUCHED**

Group PD Arrays next to the key level they align with. Highlight clusters where multiple levels and untouched zones stack.

**Workflow:**
1. Calculate key levels (Midnight Open, PDH, PDL, PD 50%, PWH, PWL, PW 50%)
2. Calculate fib retracement across the full leg (HL → HH for bullish, LH → LL for bearish)
3. Filter all levels to the correct side of price
4. Note any alignment with BOS/ChoCh levels
5. Scan PD Arrays on 4H and 15m within the indication window
6. Filter to zones overlapping a key level (±0.2% of price)
7. Note touched/untouched status

---

## Checklist

- [ ] **4H trend is clear** — HH/HL or LH/LL using pivot highs and lows. Not choppy.
- [ ] **Indication is marked** — The broken previous pivot level, not the resulting extreme
- [ ] **Phase determined in order** — Continuation first, then Correction
- [ ] **If Correction** — Correction Levels Addendum produced (mandatory)
- [ ] **If Continuation** — Trade plan produced with entry, TP, invalidation, R:R
- [ ] **15m confirms phase** — Structure aligns with expected behavior
- [ ] **Indication reclaimed** — Price has crossed back through indication level
- [ ] **Entry on pullback** — Enter on 15m pullback, not at indication price itself
- [ ] **SL at 15m structure** — Stop loss at 15m pivot HL/LH, not 4H invalidation

---

## ChoCh and BOS on the 4H

These ICT concepts map directly onto market structure and the ICC framework.

### Definitions

**ChoCh (Change of Character)** — The first break of market structure *against* the prior trend. In a downtrend making LH/LL, the first higher high breaks the pattern. This signals the old trend may be over.

**BOS (Break of Structure)** — A break of market structure *in the direction of* the current trend. Each new HH (bullish) or LL (bearish) that breaks the previous one is a BOS. It confirms the trend is continuing to make HH/HL or LH/LL.

### Identifying ChoCh After a Reversal

When a trend reverses (e.g., downtrend bottoms and starts to rally), the ChoCh is the **first pivot high that gets broken after the reversal low** — the first higher high, ending the pattern of lower highs.

Key logic:

1. **The reference must exist before the break.** After a reversal low, price rallies and forms a pivot high, then pulls back. When price breaks above that pivot high, that is the ChoCh — the first HH.

2. **Waterfall moves compress structure.** In a sharp selloff, the 4H may print sequential lower bars without clean pivot highs between them. The first pivot high that forms after the reversal low becomes the ChoCh level.

3. **ChoCh is the level that was broken, not the resulting high.** Same principle as ICC indication.

4. **BOS then confirms.** Each subsequent pivot high (bullish) or pivot low (bearish) that gets broken is a BOS — each new HH or LL confirming the trend continues.

### Relationship to ICC

- **ChoCh** = the first HH or LL — establishes that a new trend exists. Precondition for running ICC.
- **BOS** = each subsequent HH or LL — identical to an ICC **indication**. A broken pivot level confirming the trend is making new structure.
- The most recent BOS on the 4H = the ICC indication price.

---

## Rules

- Never enter during Indication or Correction — only Continuation
- Never trade a choppy 4H — no exceptions
- The indication price is the broken previous pivot level (the HH/LL that was exceeded), not the resulting new extreme
- The new extreme is the take profit target
- Invalidation is the previous HL/LH — one pivot back. If it breaks, HH/HL or LH/LL is over.
- Indication reclaim confirms continuation — it is not the entry
- Enter on the 15m pullback within continuation, not at the indication price
- Stop loss at 15m micro-structure (pivot HL/LH), not the 4H invalidation
- Correction Levels Addendum is mandatory when phase = Correction
- 4H uses pivot HL/LH (major turns), not micro swings — micro-structure is for the 15m
- PD Array scan proximity uses ±0.2% of current price to scale across instruments
