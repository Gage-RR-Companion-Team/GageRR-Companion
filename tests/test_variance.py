# tests/test_variance.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.variance import ComputeVarianceComponents

# --- Helper ---

def make_anova_table(ms_part=10.0, ms_operator=5.0, ms_interaction=1.0, ms_repeatability=0.5):
    """Build a minimal ANOVA table with controllable MS values."""
    return pd.DataFrame({
        "Source": ["Part", "Operator", "Part*Operator", "Repeatability", "Total"],
        "DF": [4, 2, 8, 15, 29],
        "SS": [ms_part*4, ms_operator*2, ms_interaction*8, ms_repeatability*15, 999],
        "MS": [ms_part, ms_operator, ms_interaction, ms_repeatability, np.nan]
    })

# --- Return structure ---

def test_returns_dataframe():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    assert isinstance(result, pd.DataFrame)

def test_has_required_columns():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    assert set(result.columns) == {"Source", "VarianceComponent", "PercentContribution"}

def test_has_seven_rows():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    assert len(result) == 7

def test_expected_sources_present():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    expected = {
        "Repeatability", "Operator", "Operator*Part Interaction",
        "Reproducibility", "Total Gage R&R", "Part-To-Part", "Total Variation"
    }
    assert set(result["Source"]) == expected

# --- Variance component formulas ---

def test_repeatability_equals_ms_repeatability():
    anova = make_anova_table(ms_repeatability=0.5)
    result = ComputeVarianceComponents(anova, 5, 3, 2)
    rep = result.loc[result["Source"] == "Repeatability", "VarianceComponent"].values[0]
    assert abs(rep - 0.5) < 1e-8

def test_reproducibility_equals_operator_plus_interaction():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Reproducibility"] - (vc["Operator"] + vc["Operator*Part Interaction"])) < 1e-8

def test_total_gage_rr_equals_repeatability_plus_reproducibility():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Total Gage R&R"] - (vc["Repeatability"] + vc["Reproducibility"])) < 1e-8

def test_total_variation_equals_gage_rr_plus_part():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    vc = result.set_index("Source")["VarianceComponent"]
    assert abs(vc["Total Variation"] - (vc["Total Gage R&R"] + vc["Part-To-Part"])) < 1e-8

# --- Percent contribution ---

def test_percent_contribution_sums_correctly():
    """Total Variation should be 100%, and Gage R&R + Part-To-Part should sum to 100%."""
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    pc = result.set_index("Source")["PercentContribution"]
    assert abs(pc["Total Variation"] - 100.0) < 1e-8
    assert abs(pc["Total Gage R&R"] + pc["Part-To-Part"] - 100.0) < 1e-8

def test_percent_contribution_all_nonnegative():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    assert (result["PercentContribution"] >= 0).all()

# --- Negative variance floored at zero ---

def test_negative_interaction_floored_to_zero():
    """MS_interaction < MS_repeatability should give zero interaction variance."""
    anova = make_anova_table(ms_interaction=0.3, ms_repeatability=0.5)
    result = ComputeVarianceComponents(anova, 5, 3, 2)
    interaction = result.loc[result["Source"] == "Operator*Part Interaction", "VarianceComponent"].values[0]
    assert interaction == 0.0

def test_negative_operator_floored_to_zero():
    """MS_operator < MS_interaction should give zero operator variance."""
    anova = make_anova_table(ms_operator=0.8, ms_interaction=1.0)
    result = ComputeVarianceComponents(anova, 5, 3, 2)
    op = result.loc[result["Source"] == "Operator", "VarianceComponent"].values[0]
    assert op == 0.0

def test_all_variance_components_nonnegative():
    result = ComputeVarianceComponents(make_anova_table(), 5, 3, 2)
    assert (result["VarianceComponent"] >= 0).all()

# --- Missing ANOVA sources ---

def test_missing_anova_source_raises():
    anova = make_anova_table().loc[lambda df: df["Source"] != "Part"]
    with pytest.raises(ValueError):
        ComputeVarianceComponents(anova, 5, 3, 2)
