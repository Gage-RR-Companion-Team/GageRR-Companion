# tests/test_tables.py
import pytest
import pandas as pd
import numpy as np
from gage_rr_companion.tables import GenerateGageRRTable

# --- Helper ---

def make_variance_components():
    """Minimal realistic variance components DataFrame."""
    return pd.DataFrame({
        "Source": [
            "Total Gage R&R",
            "Repeatability",
            "Reproducibility",
            "Operator",
            "Operator*Part",
            "Part-To-Part",
            "Total Variation"
        ],
        "VarianceComponent": [0.04, 0.02, 0.02, 0.01, 0.01, 0.16, 0.20],
        "PercentContribution": [20.0, 10.0, 10.0, 5.0, 5.0, 80.0, 100.0]
    })

# --- Return structure ---

def test_returns_dataframe():
    assert isinstance(GenerateGageRRTable(make_variance_components()), pd.DataFrame)

def test_has_required_columns():
    result = GenerateGageRRTable(make_variance_components())
    assert set(result.columns) == {
        "Source", "VarianceComponent", "PercentContribution",
        "StdDev", "StudyVar", "PercentStudyVar"
    }

def test_row_count_preserved():
    vc = make_variance_components()
    result = GenerateGageRRTable(vc)
    assert len(result) == len(vc)

# --- Computed values ---

def test_stddev_is_sqrt_of_variance():
    result = GenerateGageRRTable(make_variance_components())
    for _, row in result.iterrows():
        assert abs(row["StdDev"] - np.sqrt(row["VarianceComponent"])) < 1e-8

def test_study_var_is_6_sigma():
    result = GenerateGageRRTable(make_variance_components())
    for _, row in result.iterrows():
        assert abs(row["StudyVar"] - 6 * row["StdDev"]) < 1e-8

def test_total_variation_percent_study_var_is_100():
    result = GenerateGageRRTable(make_variance_components())
    total = result.loc[result["Source"] == "Total Variation", "PercentStudyVar"].values[0]
    assert abs(total - 100.0) < 1e-8

def test_percent_study_var_formula():
    result = GenerateGageRRTable(make_variance_components())
    total_sv = result.loc[result["Source"] == "Total Variation", "StudyVar"].values[0]
    for _, row in result.iterrows():
        expected = row["StudyVar"] / total_sv * 100
        assert abs(row["PercentStudyVar"] - expected) < 1e-8

def test_percent_study_var_all_nonnegative():
    result = GenerateGageRRTable(make_variance_components())
    assert (result["PercentStudyVar"] >= 0).all()

# --- Zero variance edge case ---

def test_zero_variance_gives_zero_stddev_and_study_var():
    vc = make_variance_components().copy()
    vc.loc[vc["Source"] == "Repeatability", "VarianceComponent"] = 0.0
    result = GenerateGageRRTable(vc)
    rep = result.loc[result["Source"] == "Repeatability"]
    assert rep["StdDev"].values[0] == 0.0
    assert rep["StudyVar"].values[0] == 0.0

# --- Validation errors ---

def test_missing_source_col_raises():
    vc = make_variance_components().drop(columns=["Source"])
    with pytest.raises(ValueError, match="Source"):
        GenerateGageRRTable(vc)

def test_missing_variance_col_raises():
    vc = make_variance_components().drop(columns=["VarianceComponent"])
    with pytest.raises(ValueError, match="VarianceComponent"):
        GenerateGageRRTable(vc)

def test_missing_percent_contribution_col_raises():
    vc = make_variance_components().drop(columns=["PercentContribution"])
    with pytest.raises(ValueError, match="PercentContribution"):
        GenerateGageRRTable(vc)

# --- Input not mutated ---

def test_input_not_modified():
    vc = make_variance_components()
    original = vc.copy()
    GenerateGageRRTable(vc)
    pd.testing.assert_frame_equal(vc, original)
