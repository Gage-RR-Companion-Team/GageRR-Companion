# tests/test_anova.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.anova import ComputeANOVA

# --- Helper ---

def make_df(operators, parts, trials, values):
    """Build a minimal long-format DataFrame."""
    return pd.DataFrame({
        "Operator": operators,
        "Part": parts,
        "Trial": trials,
        "Value": values
    })

def balanced_df():
    """2 operators, 3 parts, 2 trials each — simple balanced design."""
    rows = []
    for op in ["Alice", "Bob"]:
        for part in [1, 2, 3]:
            for trial in [1, 2]:
                rows.append((op, part, trial, float(part) + (0.1 if op == "Bob" else 0.0)))
    df = pd.DataFrame(rows, columns=["Operator", "Part", "Trial", "Value"])
    return df

# --- Return structure ---

def test_returns_dataframe():
    result = ComputeANOVA(balanced_df())
    assert isinstance(result, pd.DataFrame)

def test_has_required_columns():
    result = ComputeANOVA(balanced_df())
    assert set(result.columns) == {"Source", "DF", "SS", "MS"}

def test_has_five_rows():
    result = ComputeANOVA(balanced_df())
    assert len(result) == 5

def test_sources_are_correct():
    result = ComputeANOVA(balanced_df())
    expected = {"Part", "Operator", "Part*Operator", "Repeatability", "Total"}
    assert set(result["Source"]) == expected

def test_total_ms_is_nan():
    result = ComputeANOVA(balanced_df())
    total_ms = result.loc[result["Source"] == "Total", "MS"].values[0]
    assert np.isnan(total_ms)

# --- Degrees of freedom ---

def test_df_part():
    # 3 parts → DF = 2
    result = ComputeANOVA(balanced_df())
    df_part = result.loc[result["Source"] == "Part", "DF"].values[0]
    assert df_part == 2

def test_df_operator():
    # 2 operators → DF = 1
    result = ComputeANOVA(balanced_df())
    df_op = result.loc[result["Source"] == "Operator", "DF"].values[0]
    assert df_op == 1

def test_df_interaction():
    # (3-1)*(2-1) = 2
    result = ComputeANOVA(balanced_df())
    df_int = result.loc[result["Source"] == "Part*Operator", "DF"].values[0]
    assert df_int == 2

def test_df_repeatability():
    # 2 ops * 3 parts * (2 trials - 1) = 6
    result = ComputeANOVA(balanced_df())
    df_rep = result.loc[result["Source"] == "Repeatability", "DF"].values[0]
    assert df_rep == 6

def test_df_total():
    # 12 rows - 1 = 11
    result = ComputeANOVA(balanced_df())
    df_total = result.loc[result["Source"] == "Total", "DF"].values[0]
    assert df_total == 11

# --- SS additivity ---

def test_ss_components_sum_to_total():
    result = ComputeANOVA(balanced_df())
    ss = result.set_index("Source")["SS"]
    component_sum = ss["Part"] + ss["Operator"] + ss["Part*Operator"] + ss["Repeatability"]
    assert abs(component_sum - ss["Total"]) < 1e-8

def test_ss_all_nonnegative():
    result = ComputeANOVA(balanced_df())
    assert (result["SS"] >= -1e-10).all()

# --- MS = SS / DF ---

def test_ms_equals_ss_over_df():
    result = ComputeANOVA(balanced_df())
    for _, row in result.iterrows():
        if row["Source"] == "Total":
            continue
        assert abs(row["MS"] - row["SS"] / row["DF"]) < 1e-8

# --- Perfect repeatability case ---

def test_zero_repeatability_when_trials_identical():
    """If every operator/part cell has identical trial values, repeatability SS = 0."""
    rows = []
    for op in ["Alice", "Bob"]:
        for part in [1, 2, 3]:
            for trial in [1, 2]:
                rows.append((op, part, trial, float(part)))
    df = pd.DataFrame(rows, columns=["Operator", "Part", "Trial", "Value"])
    result = ComputeANOVA(df)
    ss_rep = result.loc[result["Source"] == "Repeatability", "SS"].values[0]
    assert abs(ss_rep) < 1e-8

# --- Custom column names ---

def test_custom_column_names():
    df = balanced_df().rename(columns={
        "Operator": "Op", "Part": "Prt", "Trial": "Rep", "Value": "Meas"
    })
    result = ComputeANOVA(df, operator_col="Op", part_col="Prt", trial_col="Rep", value_col="Meas")
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 5

# --- Input is not mutated ---

def test_input_dataframe_not_modified():
    df = balanced_df()
    original = df.copy()
    ComputeANOVA(df)
    pd.testing.assert_frame_equal(df, original)
