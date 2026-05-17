# MNQ Multi-Strategy Bot

Two trading bots sharing one FastAPI service, one Tradovate connection, one SQLite, and one set of risk guardrails.

| Bot | Endpoint | Pine indicator | Strategy |
|---|---|---|---|
| **MNQ S&D** | `POST /webhook/tradingview` | [`lux_market_structure_alerter.pine`](pine/lux_market_structure_alerter.pine) | Unmitigated 4H ChoCh/BoS zones. Resting limit at proximal edge. 3R. |
| **Silver Bullet** | `POST /webhook/silverbullet` | [`lux_silver_bullet_alerter.pine`](pine/lux_silver_bullet_alerter.pine) | 10:00–11:15 ET window. Super-Strict FVG → same-direction MSS (sequential). Stop entry at MSS candle's high/low. SL at nearest FVG edge. 2R. One trade per day. |

Both share the daily loss kill switch (`DAILY_LOSS_LIMIT_USD`). Rows tagged by `source` column in the `zones` table.

## MNQ S&D Bot

**Primary path:** a Pine v6 indicator derived from the **LuxAlgo Market Structure CHoCH/BOS (Fractal)** source (CC BY-NC-SA 4.0). It runs server-side on TradingView, fires `alert()` on every new zone and on every mitigation event, and POSTs a signed JSON payload to a Python webhook. The webhook sizes the position and places a resting limit + OCO bracket on Tradovate.

The Pine is a faithful replication of the LuxAlgo logic — same fractal detection, same crossover triggers, same "deepest pullback between fractal & break" SL definition — plus an alert layer and an array-of-zones for multi-zone mitigation. Diff our pinned upstream copy against TradingView's latest periodically (`make pine-diff`) and re-merge if LuxAlgo updates the script.

## Status

- ✅ Phase 1: Pine v6 alerter [pine/lux_market_structure_alerter.pine](pine/lux_market_structure_alerter.pine)
- ✅ Phase 2: FastAPI skeleton + webhook + SQLite (dry-run mode)
- ✅ Phase 3: Tradovate REST client + OAuth + OSO bracket
- ✅ Phase 4: Tradovate WS listener (fills/order status)
- ✅ Phase 5: Guardrails (concurrent / loss / session hours)
- ✅ Phase 6: Dockerfile + compose + Makefile
- ✅ Phase 7: MCP-driven poller as a disabled fallback ([service/poller.py](service/poller.py))

Default mode is `DRY_RUN=true` — the service logs "would place order" instead of hitting Tradovate.

## Architecture

```
TradingView (4H MNQ chart) — lux_market_structure_alerter.pine
        │
        │  alert() JSON payload  →  TradingView webhook
        ▼
ngrok → Python service on :8080
        ├─ HMAC / payload-secret verify
        ├─ SQLite (zones, orders, fills)
        ├─ Guardrails (session, concurrent, daily loss)
        ├─ Lifecycle state machine
        └─ Tradovate REST + WS (orders, fills)
```

## Setup

### Prereqs
- Python 3.10+ (Dockerfile uses 3.12)
- Tradovate demo account
- ngrok (for local development)

### Install

```bash
cd bot
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env       # then fill in
make test                  # 29 tests should pass
make dev                   # uvicorn on :8080
make ngrok                 # in another shell — exposes :8080 via https
```

### TradingView setup

1. Open the Pine editor, paste [pine/lux_market_structure_alerter.pine](pine/lux_market_structure_alerter.pine).
2. Save the script and add it to a **MNQ1! 4H chart**.
3. In the indicator settings, paste your `WEBHOOK_SECRET` value into the "Webhook shared secret" input.
4. Create an alert:
   - **Condition:** the indicator → "Any alert() function call"
   - **Webhook URL:** `https://<your-ngrok>.ngrok-free.app/webhook/tradingview`
   - **Message:** `{{alert_message}}` (the literal default — the JSON payload is built in Pine and passes through)
5. Save the alert.

Default `length = 5` matches LuxAlgo's default (p=2 each side). Adjust if you're using a different setting.

### Tradovate setup

1. Create a [Tradovate demo account](https://demo.tradovate.com).
2. Tradovate API portal → register an application → record `cid` and `sec`.
3. Fill `.env`:
   - `TRADOVATE_USERNAME`, `TRADOVATE_PASSWORD`
   - `TRADOVATE_DEVICE_ID` (any stable string, e.g. `mnq-bot-mac-01`)
   - `TRADOVATE_CID`, `TRADOVATE_SEC`
   - `TRADOVATE_ACCOUNT_ID` (find via `GET /account/list` after first login)
   - `TRADOVATE_ENV=demo`
4. Flip `DRY_RUN=false` and restart.

## Verification

### End-to-end (dry-run)

```bash
make dev
# in another terminal:
curl -X POST http://localhost:8080/webhook/tradingview \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"CME_MINI:MNQ1!","tf":"240","event":"new_zone","id":"test-1",
       "direction":"long","entry":20000.0,"sl":19995.0,"ts":1700000000,
       "secret":"<your-WEBHOOK_SECRET>"}'
curl http://localhost:8080/state | jq
```

Should see a zone `armed` with `contracts=5, tp=20015.0`.

### Tests
```bash
make test
```

## LuxAlgo upstream sync

Our Pine alerter is derived from the LuxAlgo script. To check for upstream changes:

1. Open LuxAlgo's "Market Structure CHoCH/BOS (Fractal)" on TradingView.
2. Copy the source.
3. Save into `/tmp/lux_latest.pine`.
4. `make pine-diff`.
5. If diff is non-empty: port relevant changes into `lux_market_structure_alerter.pine`, then `cp /tmp/lux_latest.pine pine/_luxalgo_upstream.pine` to re-pin.

Suggested cadence: monthly, or whenever you see unexpected zone behavior.

## Silver Bullet Bot

A second strategy in the same service: trades the ICT Silver Bullet AM window on MNQ 1-minute.

**Trigger:** Super-Strict FVG forms first → same-direction MSS (BoS/ChoCh) fires on a later bar (sequential, not simultaneous) → emit `new_signal`.

**Entry:** Stop order at the **high** (long) / **low** (short) of the MSS-confirmation candle.

**SL:** Bottom (long) / top (short) of the **nearest active Super-Strict FVG** by price.

**TP:** Fixed 2R from entry.

**Window:** Mon–Fri, 10:00–11:15 ET. Force-cancels any unfilled stop at 11:15 ET via background sweeper (`service/silverbullet/expiry.py`, runs every 30s).

**One trade per day:** the first valid trigger takes the slot — even if it skips for sizing or guardrails. No retries within the same window.

**Setup steps** (after the MNQ S&D bot is already wired):
1. Load [`pine/lux_silver_bullet_alerter.pine`](pine/lux_silver_bullet_alerter.pine) into a new TradingView Pine Editor tab.
2. Save the script and apply to a **MNQ 1m** chart.
3. Paste your `WEBHOOK_SECRET` into the indicator's "Webhook shared secret" input.
4. Create an alert: condition = "Lux SB Alerter" → "Any alert() function call". Webhook URL = `https://<your-ngrok>.ngrok-free.dev/webhook/silverbullet`. Message = `{{alert_message}}`.
5. Save. The first valid setup inside Mon–Fri 10:00–11:15 ET fires.

**License**: derivative of LuxAlgo "ICT Silver Bullet" (CC BY-NC-SA 4.0). Same constraints as the MS Fractal alerter. Pinned upstream: [`pine/_luxalgo_sb_upstream.pine`](pine/_luxalgo_sb_upstream.pine). Diff via `make pine-diff-sb`.

**Test commands:**
```
make test    # 29 + ~20 new SB tests
```

Smoke-test SB webhook in dry-run with `BYPASS_GUARDRAILS=true` (window-bypass + one-per-day-bypass both honored):
```
curl -X POST http://localhost:8080/webhook/silverbullet -H 'Content-Type: application/json' -d '{"symbol":"CME_MINI:MNQ1!","tf":"1","event":"new_signal","id":"sb-smoke","direction":"long","entry":20010.0,"sl":20000.0,"ts":1700000000,"secret":"<YOUR_SECRET>"}'
```

## Fallback: MCP-driven poller

If the webhook path breaks (TV alert quota, network issues, etc.), the original MCP-poller path is still in the repo as a fallback. To switch:

1. Set `POLLER_ENABLED=true` in `.env`.
2. Make sure TradingView Desktop is running with LuxAlgo applied on MNQ 4H.
3. The poller will call `data_get_structure_zones` every 60s and drive lifecycle the same way.

This path is rate-limited by your machine being on; the Pine path is server-side and immune to that.

## Guardrails

- Session: Sun 18:00 ET → Fri 17:00 ET (daily 17:00–18:00 ET maintenance excluded)
- Max armed orders: 3 (default — `MAX_ARMED_ORDERS`)
- Max concurrent positions: 1 (default — `MAX_CONCURRENT_POSITIONS`)
- Daily loss kill switch: −$200 (default — `DAILY_LOSS_LIMIT_USD`)

## Sizing

```
contracts = floor(RISK_PER_TRADE_USD / (risk_pts × MNQ_POINT_VALUE))
```

Default: `$50 / (risk × $2)`. If `contracts == 0` the zone is too wide for the budget — logged as `skipped_wide_zone`.

## Gotchas

1. **Pine "repaint" is not a bug.** Fractal pivots confirm `p` bars late by design. `alert.freq_once_per_bar_close` makes the alert deterministic on the confirmation bar.
2. **Token TTL ≈ 80 min.** Client refreshes proactively at ~5 min before expiry; full re-login fallback on 401.
3. **TradingView webhook IP allowlist** required on cloud hosting (not local ngrok). IPs: `52.89.214.238, 34.212.75.30, 54.218.53.128, 52.32.178.7`.
4. **Front-month rollover** (~8th of contract month): when `GET /contract/find` returns a new symbol, cancel armed orders first.
5. **Session boundary:** default TIF is `Day`. Set `TIF_OVERRIDE_GTC=true` to opt into GTC.
6. **MNQ tick = 0.25.** All prices are tick-rounded via `sizing.round_to_tick` before submission.
7. **HMAC replay:** v1 accepts replays. Rotate `WEBHOOK_SECRET` per deploy.

## License & attribution

The Pine alerter at [pine/lux_market_structure_alerter.pine](pine/lux_market_structure_alerter.pine) is a derivative work of LuxAlgo's "Market Structure CHoCH/BOS (Fractal)" — licensed CC BY-NC-SA 4.0. Pinned upstream copy: [pine/_luxalgo_upstream.pine](pine/_luxalgo_upstream.pine).

Personal use only. The NC clause prohibits commercial use; the SA clause means any redistribution must release the derivative under the same CC BY-NC-SA 4.0 license. Do not publish or share the modified script.

## Going live

Only after **≥2 weeks of clean demo PnL**:
1. Set `TRADOVATE_ENV=live`
2. Set live account credentials
3. Restart
4. Watch closely.
