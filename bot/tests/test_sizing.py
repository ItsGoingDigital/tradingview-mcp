from service.sizing import compute_risk_pts, compute_tp, contracts_for, round_to_tick


def test_round_to_tick():
    assert round_to_tick(100.13) == 100.25
    assert round_to_tick(100.12) == 100.0
    assert round_to_tick(100.0) == 100.0


def test_compute_risk_pts():
    assert compute_risk_pts(100, 95) == 5
    assert compute_risk_pts(95, 100) == 5
    assert compute_risk_pts(100, 100) == 0


def test_compute_tp_long():
    # entry 100, sl 95, risk 5 → tp = 115
    assert compute_tp(100, 95) == 115.0


def test_compute_tp_short():
    # entry 100, sl 105, risk 5 → tp = 85
    assert compute_tp(100, 105) == 85.0


def test_contracts_for_normal():
    # $50 / (5 pts × $2) = 5 contracts
    assert contracts_for(5.0, risk_usd=50, pt_val=2.0) == 5


def test_contracts_for_wide_zone():
    # $50 / (30 pts × $2) = 0.833 → floor 0 → skip
    assert contracts_for(30.0, risk_usd=50, pt_val=2.0) == 0


def test_contracts_for_zero_risk():
    assert contracts_for(0.0) == 0
    assert contracts_for(-1.0) == 0
