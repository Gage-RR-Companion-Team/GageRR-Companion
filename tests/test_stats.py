# tests/test_stats.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.stats import ComputeOperatorStats

# --- Helper ---

def make_df():
    """2 operators, 3 measurements each."""
    return pd.DataFrame({
        "Operator": ["Alice", "Alice", "Alice", "Bob", "Bob", "Bob"],
        "Value": [5.0, 5.2, 4.8, 6.0, 6.1, 5.9]
    })

# --- Return structure ---

def test_returns_dataframe():
    assert isinstance(ComputeOperatorStats(make_df()), pd.DataFrame)

def test_has_required_columns():
    result = ComputeOperatorStats(make_df())
    assert set(result.columns) == {"Operator", "Count", "Mean", "StdDev", "Min", "Max", "Range", "CV_Percent"}

def test_one_row_per_operator():
    result = ComputeOperatorStats(make_df())
    assert len(result) == 2

# --- Computed values ---

def test_count():
    result = ComputeOperatorStats(make_df())
    alice = result.loc[result["Operator"] == "Alice", "Count"].values[0]
    assert alice == 3

def test_mean():
    result = ComputeOperatorStats(make_df())
    alice = result.loc[result["Operator"] == "Alice", "Mean"].values[0]
    assert abs(alice - 5.0) < 1e-8

def test_min():
    result = ComputeOperatorStats(make_df())
    alice = result.loc[result["Operator"] == "Alice", "Min"].values[0]
    assert abs(alice - 4.8) < 1e-8

def test_max():
    result = ComputeOperatorStats(make_df())
    alice = result.loc[result["Operator"] == "Alice", "Max"].values[0]
    assert abs(alice - 5.2) < 1e-8

def test_range_equals_max_minus_min():
    result = ComputeOperatorStats(make_df())
    for _, row in result.iterrows():
        assert abs(row["Range"] - (row["Max"] - row["Min"])) < 1e-8

def test_stddev_uses_ddof1():
    result = ComputeOperatorStats(make_df())
    alice = result.loc[result["Operator"] == "Alice", "StdDev"].values[0]
    expected = np.std([5.0, 5.2, 4.8], ddof=1)
    assert abs(alice - expected) < 1e-8

def test_cv_percent():
    result = ComputeOperatorStats(make_df())
    for _, row in result.iterrows():
        expected_cv = (row["StdDev"] / row["Mean"]) * 100
        assert abs(row["CV_Percent"] - expected_cv) < 1e-8

# --- Edge cases ---

def test_single_operator():
    df = pd.DataFrame({"Operator": ["Alice"] * 4, "Value": [1.0, 2.0, 3.0, 4.0]})
    result = ComputeOperatorStats(df)
    assert len(result) == 1

def test_identical_values_zero_stddev():
    df = pd.DataFrame({"Operator": ["Alice"] * 3, "Value": [5.0, 5.0, 5.0]})
    result = ComputeOperatorStats(df)
    assert result.loc[0, "StdDev"] == 0.0
    assert result.loc[0, "Range"] == 0.0

# --- Validation errors ---

def test_missing_operator_col_raises():
    with pytest.raises(ValueError, match="Op"):
        ComputeOperatorStats(make_df(), operator_col="Op")

def test_missing_value_col_raises():
    with pytest.raises(ValueError, match="Meas"):
        ComputeOperatorStats(make_df(), value_col="Meas")

def test_empty_dataframe_raises():
    with pytest.raises(ValueError, match="empty"):
        ComputeOperatorStats(pd.DataFrame({"Operator": [], "Value": []}))

# --- Custom column names ---

def test_custom_column_names():
    df = make_df().rename(columns={"Operator": "Op", "Value": "Meas"})
    result = ComputeOperatorStats(df, operator_col="Op", value_col="Meas")
    assert "Op" in result.columns

# --- Input not mutated ---

def test_input_not_modified():
    df = make_df()
    original = df.copy()
    ComputeOperatorStats(df)
    pd.testing.assert_frame_equal(df, original)
