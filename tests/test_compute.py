# tests/test_compute.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.compute import ComputeGageRR

# --- Helper ---

def balanced_df():
    """2 operators, 3 parts, 2 trials — clean balanced design."""
    rows = []
    for op in ["Alice", "Bob"]:
        for part in [1, 2, 3]:
            for trial in [1, 2]:
                value = float(part) + (0.1 if op == "Bob" else 0.0)
                rows.append((op, part, trial, value))
    return pd.DataFrame(rows, columns=["Operator", "Part", "Trial", "Value"])

# --- Return structure ---

def test_returns_dict():
    assert isinstance(ComputeGageRR(balanced_df()), dict)

def test_has_required_keys():
    result = ComputeGageRR(balanced_df())
    expected_keys = {
        "anova_table", "variance_components", "gage_rr_table",
        "operator_stats", "summary_metrics", "metadata", "warnings"
    }
    assert set(result.keys()) == expected_keys

def test_anova_table_is_dataframe():
    assert isinstance(ComputeGageRR(balanced_df())["anova_table"], pd.DataFrame)

def test_variance_components_is_dataframe():
    assert isinstance(ComputeGageRR(balanced_df())["variance_components"], pd.DataFrame)

def test_gage_rr_table_is_dataframe():
    assert isinstance(ComputeGageRR(balanced_df())["gage_rr_table"], pd.DataFrame)

def test_operator_stats_is_dataframe():
    assert isinstance(ComputeGageRR(balanced_df())["operator_stats"], pd.DataFrame)

def test_summary_metrics_is_dict():
    assert isinstance(ComputeGageRR(balanced_df())["summary_metrics"], dict)

def test_metadata_is_dict():
    assert isinstance(ComputeGageRR(balanced_df())["metadata"], dict)

def test_warnings_is_list():
    assert isinstance(ComputeGageRR(balanced_df())["warnings"], list)

# --- Metadata values ---

def test_metadata_n_operators():
    result = ComputeGageRR(balanced_df())
    assert result["metadata"]["n_operators"] == 2

def test_metadata_n_parts():
    result = ComputeGageRR(balanced_df())
    assert result["metadata"]["n_parts"] == 3

def test_metadata_n_trials():
    result = ComputeGageRR(balanced_df())
    assert result["metadata"]["n_trials"] == 2

def test_metadata_n_measurements():
    result = ComputeGageRR(balanced_df())
    assert result["metadata"]["n_measurements"] == 12

# --- Summary metrics ---

def test_summary_metrics_has_required_keys():
    metrics = ComputeGageRR(balanced_df())["summary_metrics"]
    assert set(metrics.keys()) == {
        "PercentGageRR", "PercentRepeatability",
        "PercentReproducibility", "PercentPartToPart"
    }

def test_summary_metrics_sum_to_100():
    metrics = ComputeGageRR(balanced_df())["summary_metrics"]
    total = metrics["PercentGageRR"] + metrics["PercentPartToPart"]
    assert abs(total - 100.0) < 1e-6

def test_summary_metrics_gage_rr_equals_repeat_plus_repro():
    metrics = ComputeGageRR(balanced_df())["summary_metrics"]
    assert abs(
        metrics["PercentGageRR"] -
        (metrics["PercentRepeatability"] + metrics["PercentReproducibility"])
    ) < 1e-6

def test_summary_metrics_all_nonnegative():
    metrics = ComputeGageRR(balanced_df())["summary_metrics"]
    assert all(v >= 0 for v in metrics.values())

# --- Balanced design produces no warnings ---

def test_balanced_design_no_warnings():
    result = ComputeGageRR(balanced_df())
    assert result["warnings"] == []

# --- Unbalanced design triggers warning ---

def test_unbalanced_design_warning():
    df = balanced_df().iloc[:-1]  # drop one row to unbalance
    result = ComputeGageRR(df)
    assert len(result["warnings"]) > 0
    assert any("Unbalanced" in w for w in result["warnings"])

# --- Validation errors ---

def test_missing_column_raises():
    df = balanced_df().drop(columns=["Operator"])
    with pytest.raises(ValueError, match="Operator"):
        ComputeGageRR(df)

def test_empty_dataframe_raises():
    df = balanced_df().iloc[0:0]
    with pytest.raises(ValueError, match="empty"):
        ComputeGageRR(df)

def test_non_integer_trial_raises():
    df = balanced_df().astype({"Trial": float})
    with pytest.raises(TypeError, match="Trial"):
        ComputeGageRR(df)

def test_non_numeric_value_raises():
    df = balanced_df().astype({"Value": str})
    with pytest.raises(TypeError, match="Value"):
        ComputeGageRR(df)

# --- Custom column names ---

def test_custom_column_names():
    df = balanced_df().rename(columns={
        "Operator": "Op", "Part": "Prt", "Trial": "Rep", "Value": "Meas"
    })
    result = ComputeGageRR(df, operator_col="Op", part_col="Prt", trial_col="Rep", value_col="Meas")
    assert result["metadata"]["n_operators"] == 2

# --- Input not mutated ---

def test_input_not_modified():
    df = balanced_df()
    original = df.copy()
    ComputeGageRR(df)
    pd.testing.assert_frame_equal(df, original)
