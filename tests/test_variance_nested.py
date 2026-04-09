# tests/test_variance_nested.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.variance_nested import ComputeVarianceComponents_Nested

# --- Helper ---

def make_nested_anova_table(ms_operator=8.0, ms_part=2.0, ms_repeatability=0.5):
    """Build a minimal nested ANOVA table with controllable MS values."""
    return pd.DataFrame({
        "Source": ["Operator", "Part(Operator)", "Repeatability", "Total"],
        "DF": [1, 4, 6, 11],
        "SS": [ms_operator*1, ms_part*4, ms_repeatability*6, 999],
        "MS": [ms_operator, ms_part, ms_repeatability, np.nan]
    })

# --- Return structure ---

def test_returns_dataframe():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    assert isinstance(result, pd.DataFrame)

def test_has_required_columns():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    assert set(result.columns) == {"Source", "VarianceComponent", "PercentContribution"}

def test_has_seven_rows():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    assert len(result) == 7

def test_expected_sources_present():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    expected = {
        "Repeatability", "Operator", "Part(Operator)",
        "Reproducibility", "Total Gage R&R", "Part-To-Part", "Total Variation"
    }
    assert set(result["Source"]) == expected

# --- Variance component formulas ---

def test_repeatability_equals_ms_repeatability():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(ms_repeatability=0.5), 3, 2, 2)
    rep = result.loc[result["Source"] == "Repeatability", "VarianceComponent"].values[0]
    assert abs(rep - 0.5) < 1e-8

def test_reproducibility_equals_operator_only():
    """No interaction term — reproducibility should equal operator variance only."""
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Reproducibility"] - vc["Operator"]) < 1e-8

def test_total_gage_rr_equals_repeatability_plus_reproducibility():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Total Gage R&R"] - (vc["Repeatability"] + vc["Reproducibility"])) < 1e-8

def test_total_variation_equals_gage_rr_plus_part():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Total Variation"] - (vc["Total Gage R&R"] + vc["Part-To-Part"])) < 1e-8

# --- Percent contribution ---

def test_total_variation_percent_is_100():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    pc = result.set_index("Source")["PercentContribution"]
    assert abs(pc["Total Variation"] - 100.0) < 1e-8

def test_gage_rr_plus_part_percent_is_100():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    pc = result.set_index("Source")["PercentContribution"]
    assert abs(pc["Total Gage R&R"] + pc["Part-To-Part"] - 100.0) < 1e-8

def test_percent_contribution_all_nonnegative():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    assert (result["PercentContribution"] >= 0).all()

# --- Negative variance floored at zero ---

def test_negative_part_variance_floored_to_zero():
    """MS_part < MS_repeatability should give zero part variance."""
    anova = make_nested_anova_table(ms_part=0.3, ms_repeatability=0.5)
    result = ComputeVarianceComponents_Nested(anova, 3, 2, 2)
    part = result.loc[result["Source"] == "Part(Operator)", "VarianceComponent"].values[0]
    assert part == 0.0

def test_negative_operator_variance_floored_to_zero():
    """MS_operator < MS_part should give zero operator variance."""
    anova = make_nested_anova_table(ms_operator=1.0, ms_part=2.0)
    result = ComputeVarianceComponents_Nested(anova, 3, 2, 2)
    op = result.loc[result["Source"] == "Operator", "VarianceComponent"].values[0]
    assert op == 0.0

def test_all_variance_components_nonnegative():
    result = ComputeVarianceComponents_Nested(make_nested_anova_table(), 3, 2, 2)
    assert (result["VarianceComponent"] >= 0).all()

# --- Missing ANOVA sources ---

def test_missing_anova_source_raises():
    anova = make_nested_anova_table().loc[lambda df: df["Source"] != "Operator"]
    with pytest.raises(ValueError):
        ComputeVarianceComponents_Nested(anova, 3, 2, 2)

# --- Input not mutated ---

def test_input_not_modified():
    anova = make_nested_anova_table()
    original = anova.copy()
    ComputeVarianceComponents_Nested(anova, 3, 2, 2)
    pd.testing.assert_frame_equal(anova, original)
