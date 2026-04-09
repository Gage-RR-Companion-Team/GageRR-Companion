# tests/test_anova_nested.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.anova_nested import ComputeANOVA_Nested

# --- Helper ---

def balanced_nested_df():
    """
    2 operators, 3 parts each (nested), 2 trials per part.
    Parts 1-3 belong to Alice, Parts 4-6 belong to Bob.
    """
    rows = []
    for op, parts in [("Alice", [1, 2, 3]), ("Bob", [4, 5, 6])]:
        for part in parts:
            for trial in [1, 2]:
                value = float(part) + (0.1 if op == "Bob" else 0.0)
                rows.append((op, part, trial, value))
    return pd.DataFrame(rows, columns=["Operator", "Part", "Trial", "Value"])

# --- Return structure ---

def test_returns_dataframe():
    result = ComputeANOVA_Nested(balanced_nested_df())
    assert isinstance(result, pd.DataFrame)

def test_has_required_columns():
    result = ComputeANOVA_Nested(balanced_nested_df())
    assert set(result.columns) == {"Source", "DF", "SS", "MS"}

def test_has_four_rows():
    result = ComputeANOVA_Nested(balanced_nested_df())
    assert len(result) == 4

def test_sources_are_correct():
    result = ComputeANOVA_Nested(balanced_nested_df())
    expected = {"Operator", "Part(Operator)", "Repeatability", "Total"}
    assert set(result["Source"]) == expected

def test_no_interaction_term():
    result = ComputeANOVA_Nested(balanced_nested_df())
    assert "Part*Operator" not in result["Source"].values

def test_total_ms_is_nan():
    result = ComputeANOVA_Nested(balanced_nested_df())
    total_ms = result.loc[result["Source"] == "Total", "MS"].values[0]
    assert np.isnan(total_ms)

# --- Degrees of freedom ---

def test_df_operator():
    # a - 1 = 2 - 1 = 1
    result = ComputeANOVA_Nested(balanced_nested_df())
    df_op = result.loc[result["Source"] == "Operator", "DF"].values[0]
    assert df_op == 1

def test_df_part_operator():
    # a * (p - 1) = 2 * (3 - 1) = 4
    result = ComputeANOVA_Nested(balanced_nested_df())
    df_part = result.loc[result["Source"] == "Part(Operator)", "DF"].values[0]
    assert df_part == 4

def test_df_repeatability():
    # a * p * (r - 1) = 2 * 3 * (2 - 1) = 6
    result = ComputeANOVA_Nested(balanced_nested_df())
    df_rep = result.loc[result["Source"] == "Repeatability", "DF"].values[0]
    assert df_rep == 6

def test_df_total():
    # N - 1 = 12 - 1 = 11
    result = ComputeANOVA_Nested(balanced_nested_df())
    df_total = result.loc[result["Source"] == "Total", "DF"].values[0]
    assert df_total == 11

# --- SS additivity ---

def test_ss_components_sum_to_total():
    result = ComputeANOVA_Nested(balanced_nested_df())
    ss = result.set_index("Source")["SS"]
    component_sum = ss["Operator"] + ss["Part(Operator)"] + ss["Repeatability"]
    assert abs(component_sum - ss["Total"]) < 1e-8

def test_ss_all_nonnegative():
    result = ComputeANOVA_Nested(balanced_nested_df())
    assert (result["SS"] >= -1e-10).all()

# --- MS = SS / DF ---

def test_ms_equals_ss_over_df():
    result = ComputeANOVA_Nested(balanced_nested_df())
    for _, row in result.iterrows():
        if row["Source"] == "Total":
            continue
        assert abs(row["MS"] - row["SS"] / row["DF"]) < 1e-8

# --- Perfect repeatability ---

def test_zero_repeatability_when_trials_identical():
    rows = []
    for op, parts in [("Alice", [1, 2, 3]), ("Bob", [4, 5, 6])]:
        for part in parts:
            for trial in [1, 2]:
                rows.append((op, part, trial, float(part)))
    df = pd.DataFrame(rows, columns=["Operator", "Part", "Trial", "Value"])
    result = ComputeANOVA_Nested(df)
    ss_rep = result.loc[result["Source"] == "Repeatability", "SS"].values[0]
    assert abs(ss_rep) < 1e-8

# --- Custom column names ---

def test_custom_column_names():
    df = balanced_nested_df().rename(columns={
        "Operator": "Op", "Part": "Prt", "Trial": "Rep", "Value": "Meas"
    })
    result = ComputeANOVA_Nested(
        df, operator_col="Op", part_col="Prt", trial_col="Rep", value_col="Meas"
    )
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 4

# --- Input not mutated ---

def test_input_not_modified():
    df = balanced_nested_df()
    original = df.copy()
    ComputeANOVA_Nested(df)
    pd.testing.assert_frame_equal(df, original)
