# test_generate_gage_rr_plots.py

import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.generateplots import generateplots
import altair as alt

# -----------------------------
# Helper: create a valid dataframe
# -----------------------------
def create_valid_df():
    return pd.DataFrame({
        "Operator": ["A", "A", "B", "B"],
        "Part": [1, 2, 1, 2],
        "Trial": [1, 1, 1, 1],
        "Value": [10, 12, 11, 13]
    })

# -----------------------------
# Helper: create valid results dict
# -----------------------------
def create_valid_results():
    variance_components = pd.DataFrame({
        "Source": ["Repeatability", "Reproducibility", "Part-To-Part", "Total Gage R&R", "Total Variation"],
        "VarianceComponent": [0.5, 0.3, 1.2, 0.8, 2.0],
        "PercentContribution": [25, 15, 60, 40, 100]
    })

    return {
        "variance_components": variance_components,
        "metadata": {"n_operators": 2, "n_parts": 2, "n_trials": 1, "n_measurements": 4}
    }

# -----------------------------
# Test: normal valid input
# -----------------------------
def test_valid_input():
    df = create_valid_df()
    results = create_valid_results()
    charts = generateplots(df, results)
    
    assert isinstance(charts, dict)
    expected_keys = ["xbar_control_chart", "r_control_chart", "operator_boxplot", "variance_histogram"]
    assert all(k in charts for k in expected_keys)
    assert all(isinstance(c, alt.Chart) for c in charts.values())

# -----------------------------
# Test: non-DataFrame input
# -----------------------------
def test_non_dataframe_input():
    results = create_valid_results()
    with pytest.raises(TypeError):
        generateplots("not a df", results)

# -----------------------------
# Test: empty DataFrame
# -----------------------------
def test_empty_dataframe():
    df = pd.DataFrame()
    results = create_valid_results()
    with pytest.raises(ValueError):
        generateplots(df, results)

# -----------------------------
# Test: missing required column
# -----------------------------
@pytest.mark.parametrize("missing_col", ["Operator", "Part", "Trial", "Value"])
def test_missing_column(missing_col):
    df = create_valid_df().drop(columns=[missing_col])
    results = create_valid_results()
    with pytest.raises(ValueError):
        generateplots(df, results)

# -----------------------------
# Test: gage_rr_results not a dict
# -----------------------------
def test_invalid_results_type():
    df = create_valid_df()
    with pytest.raises(TypeError):
        generateplots(df, "not a dict")

# -----------------------------
# Test: missing required key in results
# -----------------------------
@pytest.mark.parametrize("missing_key", ["variance_components", "metadata"])
def test_missing_key_in_results(missing_key):
    df = create_valid_df()
    results = create_valid_results()
    del results[missing_key]
    with pytest.raises(ValueError):
        generateplots(df, results)

# -----------------------------
# Test: variance_components missing PercentContribution
# -----------------------------
def test_missing_percent_contribution():
    df = create_valid_df()
    results = create_valid_results()
    results["variance_components"] = results["variance_components"].drop(columns=["PercentContribution"])
    with pytest.raises(ValueError):
        generateplots(df, results)

# -----------------------------
# Test: single operator or single part
# -----------------------------
def test_single_operator_part():
    df = pd.DataFrame({
        "Operator": ["A", "A"],
        "Part": [1, 1],
        "Trial": [1, 2],
        "Value": [10, 11]
    })
    results = create_valid_results()
    charts = generateplots(df, results)
    assert all(isinstance(c, alt.Chart) for c in charts.values())

# -----------------------------
# Test: identical measurements
# -----------------------------
def test_identical_measurements():
    df = pd.DataFrame({
        "Operator": ["A", "A", "B", "B"],
        "Part": [1, 2, 1, 2],
        "Trial": [1, 1, 1, 1],
        "Value": [5, 5, 5, 5]
    })
    results = create_valid_results()
    charts = generateplots(df, results)
    assert all(isinstance(c, alt.Chart) for c in charts.values())

# -----------------------------
# Test: NaN values in Value
# -----------------------------
def test_nan_values():
    df = create_valid_df()
    df.loc[0, "Value"] = np.nan
    results = create_valid_results()
    # Should still produce charts, Altair ignores NaNs
    charts = generateplots(df, results)
    assert all(isinstance(c, alt.Chart) for c in charts.values())
