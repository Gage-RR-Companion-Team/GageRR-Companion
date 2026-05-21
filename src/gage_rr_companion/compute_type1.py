import pandas as pd
import numpy as np
import altair as alt
from scipy import stats


def compute_type1(
    study_name: str, # Name of the Gage Study as stated by the user
    user: str, # Name of the user conducting the study
    X_m: float, # The reference value or "true value" for the measurements
    units: str, # Units of measurement (e.g., "mm", "inches")
    tolerance: float, # Total tolerance (USL - LSL) for the measurement system
    data: pd.DataFrame, # DataFrame containing the measurements (single column)
    K: float = 20 # Percent of tolerance considered acceptable for measurement system variation (default = 20)
):
    """
    Compute Type 1 Gage Study statistics.

    Notes:
    - tolerance must be TOTAL tolerance (USL - LSL)
    - K is percent (default = 20)
    """

    # -----------------------------
    # Input validation
    # -----------------------------
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Data must be a pandas DataFrame.")

    if data.shape[1] != 1:
        raise ValueError("Data must have exactly one column.")

    if tolerance <= 0:
        raise ValueError("Tolerance must be greater than zero.")

    if K <= 0:
        raise ValueError("K percent must be greater than zero.")

    if len(data) < 5:
        raise ValueError("At least 5 data points are required.")

    if len(data) < 25:
        print("Warning: Fewer than 25 data points. Results may be unreliable.")

    values = data.iloc[:, 0].astype(float).dropna()

    n = len(values)

    if n < 5:
        raise ValueError("Not enough valid (non-NaN) data points.")

    # -----------------------------
    # Core statistics
    # -----------------------------
    X_bar = values.mean()
    S = values.std(ddof=1)

    if S == 0:
        raise ValueError("Standard deviation is zero. Cannot compute capability indices.")

    SV = 6 * S
    Bias = X_bar - X_m

    # -----------------------------
    # t-test (H0: Bias = 0)
    # -----------------------------
    t_stat = Bias / (S / np.sqrt(n))
    p_value = 2 * stats.t.sf(abs(t_stat), df=n - 1)

    # -----------------------------
    # Capability indices
    # -----------------------------
    C_g = ((K / 100) * tolerance) / SV

    C_gk = (((K / 200) * tolerance) - abs(Bias)) / (SV / 2)

    # -----------------------------
    # Variation metrics
    # -----------------------------
    pct_var_repeatability = (SV / tolerance) * 100

    pct_var_total = K / C_gk if C_gk > 0 else np.inf

    # -----------------------------
    # Control chart data
    # -----------------------------
    X_bar_series = pd.Series([X_bar] * n)

    LCL = X_bar_series - 3 * S
    UCL = X_bar_series + 3 * S

    control_chart_df = pd.DataFrame({
        "Measurement": values.values,
        "X_bar": X_bar_series,
        "LCL": LCL,
        "UCL": UCL
    })

    # -----------------------------
    # Results
    # -----------------------------
    results = {
        "Study Name": study_name,
        "User": user,
        "Units": units,
        "Reference Value": X_m,
        "Tolerance": tolerance,
        "K Percent": K,
        "n": n,
        "X_bar": X_bar,
        "S": S,
        "SV": SV,
        "Bias": Bias,
        "t_stat": t_stat,
        "p_value": p_value,
        "C_g": C_g,
        "C_gk": C_gk,
        "%Var (Repeatability)": pct_var_repeatability,
        "%Var (Repeatability + Bias)": pct_var_total
    }

    return results, control_chart_df


def generate_type1_run_chart(
    control_chart_df: pd.DataFrame,
    reference_value: float | None = None,
    tolerance: float | None = None,
):
    """
    Generate a Type 1 Gage Study run chart with mean, control, and spec limit lines.
    """

    if not isinstance(control_chart_df, pd.DataFrame):
        raise TypeError("control_chart_df must be a pandas DataFrame.")

    if control_chart_df.empty:
        raise ValueError("control_chart_df cannot be empty.")

    required_cols = ["Measurement", "X_bar", "LCL", "UCL"]
    for col in required_cols:
        if col not in control_chart_df.columns:
            raise ValueError(f"Required column '{col}' missing from DataFrame.")

    chart_df = control_chart_df.copy().reset_index(drop=True)
    chart_df["Run"] = range(1, len(chart_df) + 1)

    run_points = (
        alt.Chart(chart_df)
        .mark_line(point=alt.OverlayMarkDef(filled=True, size=60), color="#1f77b4")
        .encode(
            x=alt.X("Run:O", title="Run", axis=alt.Axis(labelAngle=0, labelColor="black")),
            y=alt.Y("Measurement:Q", title="Measurement", scale=alt.Scale(zero=False), axis=alt.Axis(labelColor="black")),
            tooltip=["Run", "Measurement"]
        )
    )

    control_lines = alt.layer(
        alt.Chart(chart_df).mark_rule(color="grey", strokeDash=[4,4], size=2).encode(y="mean(X_bar):Q"),
        alt.Chart(chart_df).mark_rule(color="red", size=2).encode(y="mean(UCL):Q"),
        alt.Chart(chart_df).mark_rule(color="red", size=2).encode(y="mean(LCL):Q")
    )

    layers = [run_points, control_lines]

    if reference_value is not None and tolerance is not None:
        half_tolerance = tolerance / 2
        spec_df = pd.DataFrame(
            {
                "Limit": ["USL", "LSL"],
                "Value": [
                    reference_value + half_tolerance,
                    reference_value - half_tolerance,
                ],
            }
        )
        spec_rules = (
            alt.Chart(spec_df)
            .mark_rule(color="#2ca02c", strokeDash=[8, 4], size=2)
            .encode(y="Value:Q", tooltip=["Limit", "Value"])
        )
        spec_labels = (
            alt.Chart(spec_df)
            .mark_text(align="left", dx=6, dy=-4, color="#2ca02c", fontWeight="bold")
            .encode(
                x=alt.value(8),
                y="Value:Q",
                text="Limit:N",
            )
        )
        layers.extend([spec_rules, spec_labels])

    return alt.layer(*layers).properties(
        title="Type 1 Run Chart"
    ).configure_view(
        stroke="black"
    )
