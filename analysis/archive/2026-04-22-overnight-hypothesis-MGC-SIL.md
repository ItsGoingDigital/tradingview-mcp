# MGC & SIL — Do the "Big Moves" Happen Overnight?

**Hypothesis:** Micro Gold (MGC) and Micro Silver (SIL) make their big moves overnight.

**Sample:** Hourly bars, 22 trading days, 2026-03-23 → 2026-04-22 (500 bars per symbol; hourly data buffer cap prevented going all the way back 30 trading days — findings should generalize but treat as indicative, not definitive).

**Session split:**
- **RTH / "Day"** — 09:00–15:59 ET (hourly bars starting 09:00–15:00; ~7 bars/day, ~6.5 clock hours)
- **Overnight** — everything else (16:00–08:59 ET; ~15 bars/day, ~15 clock hours)

---

## Verdict

**Directionally TRUE in absolute terms. FALSE once you normalize per clock hour.**

The raw intuition is correct: the biggest single-day displacement almost always occurs during the overnight window, and on 77–82% of days overnight outranges RTH. But this is largely because overnight is ~2.3× longer. Per hour of open trade, **RTH is the denser, more volatile window** — by ~55–60%.

In practice the two framings answer different questions:
- "Where does the biggest absolute move each day happen?" → Overnight. Confirmed.
- "Which hour of trading is more likely to produce a big move?" → RTH. By a solid margin.

---

## MGC (Micro Gold) — 22 days

|  | Overnight | RTH | Ratio |
|---|---:|---:|---:|
| Avg range (pts) | **127.4** | 85.9 | 1.48× |
| Median range (pts) | **105.3** | 81.0 | 1.30× |
| Avg \|close-open\| (pts) | **56.5** | 43.6 | 1.30× |
| Avg volume | 246,760 | 164,475 | 1.50× |
| **Avg volume / bar** | 15,920 | **23,496** | 0.68× |

- **Days ON range > RTH range:** 17 / 22 (**77%**)
- **Days ON net > RTH net:** 12 / 22 (55%)
- **Avg ON share of daily range: 82%** (median 88%)

**Time-normalized (range per clock hour):** ON 8.49 pts/hr · **RTH 13.22 pts/hr** → RTH is 56% denser per hour.

### Top 5 biggest-range days in MGC

| Date | Day range | ON range | RTH range | ON share |
|---|---:|---:|---:|---:|
| 2026-03-23 | 416.0 | **395.6** | 165.0 | **95%** |
| 2026-04-02 | 245.4 | **245.4** | 121.1 | **100%** |
| 2026-03-31 | 206.5 | 139.6 | 119.2 | 68% |
| 2026-03-27 | 204.1 | 120.8 | 144.3 | 59% |
| 2026-03-25 | 203.9 | **203.9** | 93.4 | **100%** |

On the 5 biggest-range days, overnight carried ≥95% of the range on 3 of them. The extremes strongly support the hypothesis.

---

## SIL (Micro Silver) — 22 days

|  | Overnight | RTH | Ratio |
|---|---:|---:|---:|
| Avg range ($) | **3.56** | 2.48 | 1.43× |
| Median range ($) | **3.04** | 2.33 | 1.31× |
| Avg \|close-open\| ($) | **1.88** | 1.18 | 1.59× |
| Avg volume | 51,059 | 34,299 | 1.49× |
| **Avg volume / bar** | 3,294 | **4,900** | 0.67× |

- **Days ON range > RTH range:** 18 / 22 (**82%**)
- **Days ON net > RTH net:** 15 / 22 (68%)
- **Avg ON share of daily range: 82%** (median 88%)

**Time-normalized (range per clock hour):** ON 0.24 / hr · **RTH 0.38 / hr** → RTH is 61% denser per hour.

### Top 5 biggest-range days in SIL

| Date | Day range ($) | ON range | RTH range | ON share |
|---|---:|---:|---:|---:|
| 2026-03-23 | 9.80 | **8.76** | 3.45 | **89%** |
| 2026-03-31 | 6.44 | 4.63 | 2.88 | 72% |
| 2026-04-02 | 6.35 | **6.30** | 3.60 | **99%** |
| 2026-03-26 | 5.64 | **5.35** | 3.08 | **95%** |
| 2026-04-17 | 5.47 | 4.04 | 1.99 | 74% |

Pattern is identical to MGC — the extreme-range days are almost entirely overnight events.

---

## What This Means Practically

1. **Gap risk is real.** If you hold MGC/SIL through the close, you're exposed to the window where ~82% of the daily range, on average, is built. The top-5 days on both tickers show single-session overnight moves that dwarf full RTH ranges.

2. **RTH is not "quiet."** Per hour of clock time, the US session is the *most* volatile and *most* liquid slice of the day (vol/bar ~1.5× higher than ON). The overnight lead in absolute terms is a duration artifact.

3. **The "big move" signature is bimodal.** Most overnight moves are distributed trickle (low vol/hr but many hours). A minority are impulse events — econ data at 08:30 ET, Asian open, London fix — that appear as single-bar outliers. Those impulse events are what you "feel" when you say metals move overnight.

4. **For the Playbook framing:** Entries late in RTH that target overnight magnets (MO, PWH/PWL) are supported by this data. Overnight spans the window where levels most commonly get taken.

---

## Methodology Notes

- **Symbols:** `MGC1!`, `SIL1!` (continuous contracts, Globex).
- **Bars:** 500 hourly each (TradingView cap for direct-bar extraction), covering 2026-03-20 → 2026-04-22 calendar, 22 full trading days with both ON and RTH populated.
- **Session attribution:** a bar at hour H ET belongs to the day whose RTH it brackets — H ≤ 9 → that calendar day; H ≥ 16 → next calendar day. Days are skipped if either session has no bars (weekends, holidays).
- **Caveats:**
  - 22 days, not 30. Extending requires manually scrolling hourly data back 2+ weeks beyond what's in TradingView's hourly cache.
  - The sample period coincides with a volatile metals regime (MGC range 4100–4914 over the window). Relative ON/RTH proportions should be stable across regimes, but absolute per-day ranges here are elevated.
  - 16:00–17:59 ET daily halt bars are sparse/empty and fall into the ON bucket by construction — this slightly pads ON's absolute numbers but not per-hour figures.

Raw bars: `/tmp/mgc_bars.json`, `/tmp/sil_bars.json`. Analysis: `/tmp/overnight_analysis.py`.
