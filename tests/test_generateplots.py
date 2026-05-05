# test_generate_gage_rr_plots.py

import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.generateplots import generateplots
from gage_rr_companion.compute_type1 import compute_type1, generate_type1_run_chart
import altair as alt

# -----------------------------
# Helper: create a valid dataframe
# -----------------------------
def create_valid_df(n_operators=2, n_parts=2, n_trials=2, identical=False, nan_indices=None):
    """
    Generates a DataFrame suitable for generateplots.

    Parameters:
        n_operators (int): Number of operators (e.g., 2 = A,B)
        n_parts (int): Number of parts
        n_trials (int): Number of trials per part/operator
        identical (bool): If True, all values are identical
        nan_indices (list): List of row indices to set as NaN
    """
    data = []
    value = 10 if not identical else 5
    for op in range(n_operators):
        for part in range(1, n_parts + 1):
            for trial in range(1, n_trials + 1):
                data.append({
                    "Operator": chr(65 + op),
                    "Part": part,
                    "Trial": trial,
                    "Value": value
                })
    df = pd.DataFrame(data)
    
    if nan_indices:
        df.loc[nan_indices, "Value"] = np.nan
    
    return df

# -----------------------------
# Helper: create valid results dict
# -----------------------------
def create_valid_results(n_operators=2, n_parts=2, n_trials=2):
    variance_components = pd.DataFrame({
        "Source": ["Repeatability", "Reproducibility", "Part-To-Part", "Total Gage R&R", "Total Variation"],
        "VarianceComponent": [0.5, 0.3, 1.2, 0.8, 2.0],
        "PercentContribution": [25, 15, 60, 40, 100]
    })

    n_measurements = n_operators * n_parts * n_trials
    return {
        "variance_components": variance_components,
        "metadata": {"n_operators": n_operators, "n_parts": n_parts, "n_trials": n_trials, "n_measurements": n_measurements}
    }

# -----------------------------
# Helper: assert charts
# -----------------------------
def assert_charts(charts):
    for name, chart in charts.items():
        assert isinstance(chart, (alt.Chart, alt.LayerChart)), f"{name} is not a chart"


def create_valid_type1_control_chart_df():
    type1_data = pd.DataFrame({"Measurement": [10.01, 9.99, 10.02, 10.00, 10.01]})
    _, control_chart_df = compute_type1(
        study_name="Type 1 Test",
        user="Tester",
        X_m=10.0,
        units="mm",
        tolerance=1.0,
        data=type1_data,
    )
    return control_chart_df

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
    assert_charts(charts)

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
# Test: single operator
# -----------------------------
def test_single_operator_part():
    df = create_valid_df(n_operators=1, n_parts=2, n_trials=2)
    results = create_valid_results(n_operators=1, n_parts=2, n_trials=2)
    charts = generateplots(df, results)
    assert_charts(charts)

# -----------------------------
# Test: identical measurements
# -----------------------------
def test_identical_measurements():
    df = create_valid_df(identical=True)
    results = create_valid_results()
    charts = generateplots(df, results)
    assert_charts(charts)

# -----------------------------
# Test: NaN values in Value
# -----------------------------
def test_nan_values():
    # n_trials >= 3 to allow dropping 1 NaN and still have >=2 replicates
    df = create_valid_df(n_trials=3, nan_indices=[0])
    results = create_valid_results(n_trials=3)
    charts = generateplots(df, results)
    assert_charts(charts)


def test_type1_run_chart_valid_input():
    control_chart_df = create_valid_type1_control_chart_df()
    chart = generate_type1_run_chart(control_chart_df)
    assert isinstance(chart, alt.LayerChart)


def test_type1_run_chart_missing_required_column():
    control_chart_df = create_valid_type1_control_chart_df().drop(columns=["UCL"])
    with pytest.raises(ValueError):
        generate_type1_run_chart(control_chart_df)
