import numpy as np
import pandas as pd
import pytest
from scipy import stats

from gage_rr_companion.compute_type1 import compute_type1


def test_compute_type1_calculations_match_expected_formulas():
    data = pd.DataFrame({"Measurement": [10.01, 9.99, 10.02, 10.00, 10.01]})

    results, control_chart_df = compute_type1(
        study_name="Type 1 Test",
        user="Tester",
        X_m=10.0,
        units="mm",
        tolerance=1.0,
        data=data,
        K=20.0,
    )

    values = data["Measurement"]
    x_bar = values.mean()
    sample_std = values.std(ddof=1)
    study_variation = 6 * sample_std
    bias = x_bar - 10.0
    t_stat = bias / (sample_std / np.sqrt(len(values)))
    p_value = 2 * stats.t.sf(abs(t_stat), df=len(values) - 1)
    c_g = (0.20 * 1.0) / study_variation
    c_gk = ((0.10 * 1.0) - abs(bias)) / (study_variation / 2)

    assert results["n"] == 5
    assert results["X_bar"] == pytest.approx(x_bar)
    assert results["S"] == pytest.approx(sample_std)
    assert results["SV"] == pytest.approx(study_variation)
    assert results["Bias"] == pytest.approx(bias)
    assert results["t_stat"] == pytest.approx(t_stat)
    assert results["p_value"] == pytest.approx(p_value)
    assert results["C_g"] == pytest.approx(c_g)
    assert results["C_gk"] == pytest.approx(c_gk)
    assert results["%Var (Repeatability)"] == pytest.approx(study_variation * 100)
    assert results["%Var (Repeatability + Bias)"] == pytest.approx(20.0 / c_gk)
    assert results["Reference Value"] == 10.0
    assert results["Tolerance"] == 1.0
    assert results["K Percent"] == 20.0

    assert list(control_chart_df.columns) == ["Measurement", "X_bar", "LCL", "UCL"]
    assert control_chart_df["X_bar"].iloc[0] == pytest.approx(x_bar)
    assert control_chart_df["LCL"].iloc[0] == pytest.approx(x_bar - 3 * sample_std)
    assert control_chart_df["UCL"].iloc[0] == pytest.approx(x_bar + 3 * sample_std)


def test_compute_type1_validates_positive_tolerance_and_k():
    data = pd.DataFrame({"Measurement": [1, 2, 3, 4, 5]})

    with pytest.raises(ValueError, match="Tolerance"):
        compute_type1("Study", "Tester", 3.0, "mm", 0, data)

    with pytest.raises(ValueError, match="K percent"):
        compute_type1("Study", "Tester", 3.0, "mm", 1.0, data, K=0)


def test_compute_type1_reports_infinite_repeatability_bias_when_cgk_is_negative():
    data = pd.DataFrame({"Measurement": [0.5, 0.1, 0.2, 0.7, 0.1, 0.5]})

    results, _ = compute_type1(
        study_name="Type 1 Test",
        user="Tester",
        X_m=0.53,
        units="in",
        tolerance=0.106,
        data=data,
        K=20.0,
    )

    assert results["C_gk"] < 0
    assert np.isinf(results["%Var (Repeatability + Bias)"])
