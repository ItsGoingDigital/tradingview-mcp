.PHONY: dev test ngrok fmt db-reset install

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e . --group dev

dev:
	$(PYTHON) -m uvicorn service.main:app --reload --host 0.0.0.0 --port 8080

test:
	$(PYTHON) -m pytest -q

ngrok:
	ngrok http 8080

fmt:
	ruff format . && ruff check --fix .

db-reset:
	rm -f bot.db && $(PYTHON) -c "from service.db import init; init()"

# Diff the upstream LuxAlgo MS Fractal source we pinned against a fresh copy.
# Workflow: paste the latest LuxAlgo source into /tmp/lux_latest.pine, then:
#   make pine-diff
# If diff is non-empty, port the relevant changes into lux_market_structure_alerter.pine
# and then `cp /tmp/lux_latest.pine pine/_luxalgo_upstream.pine` to re-pin.
pine-diff:
	@test -f /tmp/lux_latest.pine || (echo "Paste latest LuxAlgo source into /tmp/lux_latest.pine first" && exit 1)
	@diff -u pine/_luxalgo_upstream.pine /tmp/lux_latest.pine || true

# Same workflow for the Silver Bullet upstream pin.
# Paste latest LuxAlgo "ICT Silver Bullet" source into /tmp/lux_sb_latest.pine first.
pine-diff-sb:
	@test -f /tmp/lux_sb_latest.pine || (echo "Paste latest LuxAlgo SB source into /tmp/lux_sb_latest.pine first" && exit 1)
	@diff -u pine/_luxalgo_sb_upstream.pine /tmp/lux_sb_latest.pine || true
