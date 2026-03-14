# tests/test_interpret_gage_rr.py

import pytest
import numpy as np
import re
from gage_rr_companion.interpret_gage_rr import interpret_gage_rr

# -----------------------------
# Helper: create a results dictionary
# -----------------------------
def create_results(
    percent_gage_rr=12.5,
    percent_repeat=8.0,
    percent_repro=4.5,
    percent_part=87.5,
    inject_nan=False,
    missing_key=None
):
    metrics = {
        "PercentGageRR": np.nan if inject_nan and missing_key != "PercentGageRR" else percent_gage_rr,
        "PercentRepeatability": np.nan if inject_nan and missing_key != "PercentRepeatability" else percent_repeat,
        "PercentReproducibility": np.nan if inject_nan and missing_key != "PercentReproducibility" else percent_repro,
        "PercentPartToPart": np.nan if inject_nan and missing_key != "PercentPartToPart" else percent_part,
    }

    if missing_key:
        metrics.pop(missing_key, None)

    return {"summary_metrics": metrics}

# -----------------------------
# 1. Normal valid input
# -----------------------------
def test_valid_input():
    results = create_results()
    interp = interpret_gage_rr(results)

    assert isinstance(interp, dict)
    for key in ["overall_status", "gage_rr_status", "root_cause", "discrimination", "recommendation"]:
        assert key in interp

    assert interp["gage_rr_status"] == "Marginal"
    assert interp["root_cause"] == "Equipment variation dominates"
    assert interp["discrimination"] == "Good"
    assert interp["overall_status"] == "Measurement system conditionally acceptable"

# -----------------------------
# 2. NaN metrics raise ValueError
# -----------------------------
@pytest.mark.parametrize(
    "key",
    ["PercentGageRR", "PercentRepeatability", "PercentReproducibility", "PercentPartToPart"]
)
def test_nan_metrics(key):
    results = create_results()
    results["summary_metrics"][key] = np.nan

    with pytest.raises(ValueError, match=re.escape(f"Metric '{key}' is missing or NaN.")):
        interpret_gage_rr(results)

# -----------------------------
# 3. Missing metric keys raise KeyError
# -----------------------------
@pytest.mark.parametrize(
    "missing_key",
    ["PercentGageRR", "PercentRepeatability", "PercentReproducibility", "PercentPartToPart"]
)
def test_missing_metric_keys(missing_key):
    results = create_results(missing_key=missing_key)
    with pytest.raises(KeyError, match=re.escape(f"Missing required summary metric: '{missing_key}'")):
        interpret_gage_rr(results)

# -----------------------------
# 4. Edge cases for Gage R&R thresholds
# -----------------------------
@pytest.mark.parametrize(
    "gage_rr,expected_status",
    [(5, "Acceptable"), (10, "Marginal"), (30, "Marginal"), (35, "Not Acceptable")]
)
def test_gage_rr_thresholds(gage_rr, expected_status):
    results = create_results(percent_gage_rr=gage_rr)
    interp = interpret_gage_rr(results)
    assert interp["gage_rr_status"] == expected_status

# -----------------------------
# 5. Edge cases for Part-To-Part discrimination
# -----------------------------
@pytest.mark.parametrize(
    "part_pct,expected_disc",
    [(90, "Good"), (70, "Moderate"), (40, "Poor")]
)
def test_part_to_part_discrimination(part_pct, expected_disc):
    results = create_results(percent_part=part_pct)
    interp = interpret_gage_rr(results)
    assert interp["discrimination"] == expected_disc

# -----------------------------
# 6. Root cause logic
# -----------------------------
def test_root_cause_equipment_dominant():
    results = create_results(percent_repeat=9, percent_repro=4)
    interp = interpret_gage_rr(results)
    assert interp["root_cause"] == "Equipment variation dominates"

def test_root_cause_operator_dominant():
    results = create_results(percent_repeat=4, percent_repro=9)
    interp = interpret_gage_rr(results)
    assert interp["root_cause"] == "Operator variation dominates"

def test_root_cause_balanced():
    results = create_results(percent_repeat=5, percent_repro=5)
    interp = interpret_gage_rr(results)
    assert interp["root_cause"] == "Balanced measurement variation"

# -----------------------------
# 7. Overall system classification logic
# -----------------------------
def test_overall_system_not_acceptable():
    results = create_results(percent_gage_rr=35, percent_part=85)
    interp = interpret_gage_rr(results)
    assert interp["overall_status"] == "Measurement system NOT acceptable"

def test_overall_system_acceptable():
    results = create_results(percent_gage_rr=5, percent_part=85)
    interp = interpret_gage_rr(results)
    assert interp["overall_status"] == "Measurement system acceptable"

def test_overall_system_conditionally_acceptable():
    results = create_results(percent_gage_rr=12, percent_part=70)
    interp = interpret_gage_rr(results)
    assert interp["overall_status"] == "Measurement system conditionally acceptable"

# -----------------------------
# 8. Recommendation text logic
# -----------------------------
def test_recommendation_equipment():
    results = create_results(percent_repeat=8, percent_repro=4)
    interp = interpret_gage_rr(results)
    assert "instrument precision" in interp["recommendation"]

def test_recommendation_operator():
    results = create_results(percent_repeat=4, percent_repro=8)
    interp = interpret_gage_rr(results)
    assert "retrain operators" in interp["recommendation"]

def test_recommendation_poor_discrimination():
    results = create_results(percent_repeat=5, percent_repro=5, percent_part=40)
    interp = interpret_gage_rr(results)
    assert "span the full expected range" in interp["recommendation"]

def test_recommendation_acceptable():
    results = create_results(percent_repeat=5, percent_repro=5, percent_part=85)
    interp = interpret_gage_rr(results)
    assert "generally acceptable" in interp["recommendation"]
