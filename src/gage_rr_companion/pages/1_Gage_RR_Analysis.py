import json
import math
import streamlit as st
import pandas as pd

from gage_rr_companion.cornelius import call_agent, get_agent_backend, load_ai_secrets
from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.compute_nested import ComputeGageRR_Nested
from gage_rr_companion.compute_type1 import compute_type1, generate_type1_run_chart
from gage_rr_companion.gage_rr_io import (
    clean_uploaded_template_table,
    load_gage_rr_data,
    load_uploaded_table,
)
from gage_rr_companion.interpret_gage_rr import interpret_gage_rr
from gage_rr_companion.generateplots import generateplots


st.set_page_config(page_title="Gage R&R Companion", layout="wide")
load_ai_secrets()

st.title("Gage R&R Analysis")
st.write("Upload a CSV or Excel file and select the type of Gage study to run.")

uploaded_file = st.file_uploader(
    "Upload your data file",
    type=["csv", "xlsx", "xlsm", "xls"],
)

study_type = st.selectbox(
    "Select study type",
    [
        "Crossed Gage R&R",
        "Nested Gage R&R",
        "Type 1 Gage Study",
        "Expanded Gage R&R",
    ],
)

st.page_link(
    "pages/2_Documentation.py",
    label="Need help with formatting? Check out the documentation page!",
)


def apply_cornelius_runtime_settings() -> str:
    """Use chat-page GUI settings when they exist, then return the active backend."""
    backend = st.session_state.get("cornelius_backend", get_agent_backend())
    if backend == "auto":
        backend = "openai_compatible"

    import os

    os.environ["CORNELIUS_BACKEND"] = backend

    openai_base = st.session_state.get("openai_compatible_api_base")
    openai_key = st.session_state.get("openai_compatible_api_key")
    if openai_base is not None:
        os.environ["OPENAI_COMPATIBLE_API_BASE"] = str(openai_base).strip()
    if openai_key is not None:
        os.environ["OPENAI_COMPATIBLE_API_KEY"] = str(openai_key).strip()

    hf_token = st.session_state.get("hf_api_token")
    hf_endpoint = st.session_state.get("hf_endpoint_url")
    hf_provider = st.session_state.get("hf_provider")
    if hf_token is not None:
        os.environ["HUGGINGFACE_API_TOKEN"] = str(hf_token).strip()
    if hf_endpoint is not None:
        os.environ["HF_ENDPOINT_URL"] = str(hf_endpoint).strip()
    if hf_provider is not None:
        os.environ["HF_PROVIDER"] = str(hf_provider).strip()

    return backend


def cornelius_followup_prompt(
    study_type: str,
    results: dict,
    interpretation: dict,
    measurement_context: dict | None = None,
) -> str:
    """Build a model-friendly prompt from computed Gage R&R results."""
    payload = {
        "study_type": study_type,
        "measurement_context": measurement_context or {},
        "summary_metrics": results.get("summary_metrics", {}),
        "interpretation": interpretation,
        "metadata": results.get("metadata", {}),
        "warnings": results.get("warnings", []),
    }
    return (
        "Given these Gage R&R analysis results, write practical recommended "
        "follow-up actions for the user. Be specific, explain what the results "
        "suggest, and describe what to investigate next. Use concise paragraphs "
        "or bullets as appropriate and stay focused on measurement system "
        "analysis. In the follow-up actions, call the device/process the "
        "\"measurement system\" instead of \"gage\".\n\n"
        f"{json.dumps(payload, default=str)}"
    )


def get_cornelius_followup(
    study_type: str,
    results: dict,
    interpretation: dict,
    measurement_context: dict | None = None,
) -> str:
    backend = apply_cornelius_runtime_settings()
    prompt = cornelius_followup_prompt(
        study_type,
        results,
        interpretation,
        measurement_context,
    )
    cache_key = json.dumps(
        {
            "backend": backend,
            "prompt": prompt,
        },
        sort_keys=True,
    )

    if "cornelius_followups" not in st.session_state:
        st.session_state.cornelius_followups = {}
    if cache_key not in st.session_state.cornelius_followups:
        st.session_state.cornelius_followups[cache_key] = call_agent(
            prompt,
            max_tokens=None,
            history=[],
            backend=backend,
        )
    return st.session_state.cornelius_followups[cache_key]


def render_cornelius_followup(markdown_text: str) -> None:
    st.markdown("**Cornelius follow-up actions**")
    with st.container(height=240, border=True):
        st.markdown(markdown_text)


def type1_total_tolerance(
    standard_value: float,
    tolerance_half_width: float,
    tolerance_mode: str,
) -> float:
    """Convert a one-sided Type 1 tolerance input into total tolerance."""
    if tolerance_mode == "+/- percent":
        tolerance = 2 * abs(standard_value) * (tolerance_half_width / 100)
        if tolerance <= 0:
            raise ValueError(
                "Percent tolerance requires a non-zero measurement standard value (X_m)."
            )
        return tolerance
    return 2 * tolerance_half_width


def interpret_type1_results(results: dict) -> dict:
    """Create Type 1 diagnostics in the same shape as standard Gage R&R output."""
    c_g = results["C_g"]
    c_gk = results["C_gk"]
    p_value = results["p_value"]

    if c_g >= 1.33 and c_gk >= 1.33:
        capability_status = "Acceptable"
        overall_status = "Measurement system acceptable"
    elif c_g >= 1.0 and c_gk >= 1.0:
        capability_status = "Marginal"
        overall_status = "Measurement system conditionally acceptable"
    else:
        capability_status = "Not Acceptable"
        overall_status = "Measurement system NOT acceptable"

    if p_value < 0.05:
        bias_status = "Statistically significant bias detected"
    else:
        bias_status = "No statistically significant bias detected"

    if c_gk <= 0:
        root_cause = "Bias is larger than the allowable bias given the tolerance."
    elif c_g < 1.0:
        root_cause = "Poor repeatability due to significant measurement variation compared to the tolerance."
    elif c_gk < c_g:
        root_cause = "Bias is reducing the capability of the measurement system."
    else:
        root_cause = "Repeatability and bias are controlled for this reference part."

    if capability_status == "Acceptable" and p_value >= 0.05:
        recommendation = "Continue monitoring with the current measurement method."
    elif p_value < 0.05:
        recommendation = "Investigate calibration, reference standard alignment, and measurement bias."
    else:
        recommendation = "Resolve measurement system bias before using for production decisions."

    return {
        "overall_status": overall_status,
        "gage_rr_status": capability_status,
        "root_cause": root_cause,
        "discrimination": bias_status,
        "recommendation": recommendation,
    }


def type1_results_for_cornelius(results: dict, measurement_name: str) -> dict:
    """Reshape Type 1 results into the generic result payload used by Cornelius."""
    return {
        "summary_metrics": {
            "C_g": results["C_g"],
            "C_gk": results["C_gk"],
            "Bias": results["Bias"],
            "p_value": results["p_value"],
            "PercentRepeatability": results["%Var (Repeatability)"],
            "PercentRepeatabilityPlusBias": results["%Var (Repeatability + Bias)"],
        },
        "metadata": {
            "study_name": results["Study Name"],
            "user": results["User"],
            "measurement_name": measurement_name,
            "units": results["Units"],
            "reference_value": results["Reference Value"],
            "total_tolerance": results["Tolerance"],
            "k_percent": results["K Percent"],
            "n": results["n"],
            "mean": results["X_bar"],
            "standard_deviation": results["S"],
            "study_variation": results["SV"],
            "t_stat": results["t_stat"],
        },
        "warnings": [],
    }


def format_type1_metric(value: float, suffix: str = "", digits: int = 4) -> str:
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return "Not meaningful"
    return f"{value:.{digits}f}{suffix}"


def display_standard_gage_results(df, results, measurement_context: dict | None = None):
    """Display shared output for crossed and nested Gage R&R."""

    interpretation = interpret_gage_rr(results)

    st.subheader("Summary Metrics")
    metrics = results["summary_metrics"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("% Gage R&R", f"{metrics['PercentGageRR']:.2f}%")
    col2.metric("% Repeatability", f"{metrics['PercentRepeatability']:.2f}%")
    col3.metric("% Reproducibility", f"{metrics['PercentReproducibility']:.2f}%")
    col4.metric("% Part-to-Part", f"{metrics['PercentPartToPart']:.2f}%")

    st.subheader("Interpretation")

    overall_status = interpretation["overall_status"]

    if "NOT acceptable" in overall_status:
        st.error(overall_status)
    elif "conditionally acceptable" in overall_status:
        st.warning(overall_status)
    else:
        st.success(overall_status)

    left, right = st.columns(2)

    with left:
        st.markdown(f"**Gage R&R Status**  \n{interpretation['gage_rr_status']}")
        st.markdown(f"**Root Cause**  \n{interpretation['root_cause']}")

    with right:
        st.markdown(f"**Discrimination**  \n{interpretation['discrimination']}")
        with st.spinner("Cornelius is reviewing the results..."):
            followup = get_cornelius_followup(
                study_type,
                results,
                interpretation,
                measurement_context,
            )
        render_cornelius_followup(followup)

    st.subheader("Plots")

    try:
        plots = generateplots(df, results)

        plot_col1, plot_col2 = st.columns(2)

        with plot_col1:
            st.altair_chart(plots["xbar_control_chart"], use_container_width=True)
            st.altair_chart(plots["operator_boxplot"], use_container_width=True)

        with plot_col2:
            st.altair_chart(plots["r_control_chart"], use_container_width=True)
            st.altair_chart(plots["variance_histogram"], use_container_width=True)

    except Exception as plot_error:
        st.warning(f"Some plots could not be generated: {plot_error}")

    with st.expander("Detailed Results", expanded=False):
        tabs = st.tabs(
            [
                "ANOVA Table",
                "Variance Components",
                "Gage R&R Table",
                "Operator Statistics",
                "Metadata",
                "Warnings",
            ]
        )

        with tabs[0]:
            if "anova_table" in results:
                st.dataframe(results["anova_table"], use_container_width=True)
            else:
                st.info("No ANOVA table available.")

        with tabs[1]:
            st.dataframe(results["variance_components"], use_container_width=True)

        with tabs[2]:
            st.dataframe(results["gage_rr_table"], use_container_width=True)

        with tabs[3]:
            st.dataframe(results["operator_stats"], use_container_width=True)

        with tabs[4]:
            st.json(results.get("metadata", {}))

        with tabs[5]:
            warnings = results.get("warnings", [])
            if warnings:
                for warning in warnings:
                    st.warning(warning)
            else:
                st.success("No warnings.")


def display_type1_results(results, control_chart_df, measurement_name: str):
    """Display Type 1 Gage Study output."""

    interpretation = interpret_type1_results(results)

    st.subheader("Summary Metrics")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(r"C$_g$", format_type1_metric(results["C_g"]))
    col2.metric(r"C$_{gk}$", format_type1_metric(results["C_gk"]))
    col3.metric("Bias", format_type1_metric(results["Bias"]))
    col4.metric("p-value", format_type1_metric(results["p_value"]))

    col9, col10 = st.columns(2)
    col9.metric(
        "% Var Repeatability",
        format_type1_metric(results["%Var (Repeatability)"], "%", digits=2),
    )
    col10.metric(
        "% Var Repeatability + Bias",
        format_type1_metric(
            results["%Var (Repeatability + Bias)"],
            "%",
            digits=2,
        ),
    )

    st.subheader("Interpretation")

    overall_status = interpretation["overall_status"]
    if "NOT acceptable" in overall_status:
        st.error(overall_status)
    elif "conditionally acceptable" in overall_status:
        st.warning(overall_status)
    else:
        st.success(overall_status)

    st.subheader("Plots")
    try:
        st.altair_chart(
            generate_type1_run_chart(
                control_chart_df,
                reference_value=results["Reference Value"],
                tolerance=results["Tolerance"],
            ),
            use_container_width=True,
        )
    except Exception as plot_error:
        st.warning(f"Type 1 run chart could not be generated: {plot_error}")

    left, right = st.columns(2)

    with left:
        st.markdown(f"**Type 1 Capability**  \n{interpretation['gage_rr_status']}")
        st.markdown(f"**Bias Check**  \n{interpretation['discrimination']}")
        st.markdown(f"**Root Cause**  \n{interpretation['root_cause']}")

    with right:
        with st.spinner("Cornelius is reviewing the results..."):
            followup = get_cornelius_followup(
                "Type 1 Gage Study",
                type1_results_for_cornelius(results, measurement_name),
                interpretation,
                {
                    "measurement_name": measurement_name,
                    "units": results["Units"],
                },
            )
        render_cornelius_followup(followup)

    with st.expander("Detailed Results", expanded=False):
        st.dataframe(pd.DataFrame([results]), use_container_width=True)


if uploaded_file is not None:
    try:
        if study_type in ["Crossed Gage R&R", "Nested Gage R&R"]:
            with st.spinner(f"Running {study_type} analysis..."):
                df = load_gage_rr_data(uploaded_file, is_path=False)
                measurement_context = {
                    "measurement_name": "Value",
                    "units": "",
                }

                if study_type == "Crossed Gage R&R":
                    results = ComputeGageRR(df)
                else:
                    results = ComputeGageRR_Nested(df)

            display_standard_gage_results(df, results, measurement_context)

        elif study_type == "Type 1 Gage Study":
            raw_df = clean_uploaded_template_table(
                load_uploaded_table(uploaded_file, is_path=False)
            )

            st.subheader("Type 1 Study Inputs")

            measurement_options = [
                column
                for column in raw_df.columns
                if str(column).strip().lower() not in {"test #", "test#", "test number"}
            ]
            if not measurement_options:
                raise ValueError("Type 1 data must include a measurement column.")

            measurement_col = st.selectbox(
                "Measurement column",
                measurement_options,
                help=(
                    "The single column of repeated measurements from one operator. "
                    "Type 1 studies should ideally use more than 25 repeated measurements."
                ),
            )

            study_name = st.text_input(
                "Study name",
                value="Type 1 Gage Study",
                help="The name used to identify this Type 1 Gage Study in the results.",
            )
            user = st.text_input(
                "Reported by",
                value="",
                help="The person conducting or reporting the one-operator Type 1 study.",
            )
            units = st.text_input(
                "Units",
                value="",
                help="The measurement units for the repeated readings, such as mm, inches, or mS/cm.",
            )
            x_m = st.number_input(
                "Measurement standard value (X_m)",
                value=0.0,
                help="The known reference or true value of the reliable calibration or validated standard.",
            )

            tolerance_unit_label = f"+/- {units.strip()}" if units.strip() else "+/- units"
            tolerance_mode_options = {
                tolerance_unit_label: "+/- units",
                "+/- percent": "+/- percent",
            }
            tolerance_value_col, tolerance_format_col = st.columns([2, 1])
            with tolerance_value_col:
                tolerance_half_width = st.number_input(
                    "Tolerance (+/-)",
                    value=1.0,
                    min_value=0.000001,
                    help=(
                        "For +/- units, enter the allowed absolute difference from the standard. "
                        "For +/- percent, enter the percent of the standard value."
                    ),
                )
            with tolerance_format_col:
                tolerance_mode_label = st.selectbox(
                    "Tolerance format",
                    list(tolerance_mode_options),
                    help=(
                        "Enter the one-sided tolerance around the standard value. "
                        "The app converts it to total tolerance for the Type 1 calculation."
                    ),
                )
                tolerance_mode = tolerance_mode_options[tolerance_mode_label]

            if st.button("Run Type 1 Gage Study"):
                with st.spinner("Running Type 1 Gage Study..."):
                    type1_data = raw_df[[measurement_col]].copy().dropna()
                    tolerance = type1_total_tolerance(
                        x_m,
                        tolerance_half_width,
                        tolerance_mode,
                    )

                    results, control_chart_df = compute_type1(
                        study_name=study_name,
                        user=user,
                        X_m=x_m,
                        units=units,
                        tolerance=tolerance,
                        data=type1_data,
                        K=20.0,
                    )

                display_type1_results(results, control_chart_df, str(measurement_col))

        elif study_type == "Expanded Gage R&R":
            raw_df = clean_uploaded_template_table(
                load_uploaded_table(uploaded_file, is_path=False)
            )

            st.subheader("Expanded Gage R&R Setup")

            st.info(
                "Expanded Gage R&R setup UI is available, but the compute engine "
                "must be connected after compute_expanded.py is implemented."
            )

            value_col = st.selectbox("Measurement column", raw_df.columns)
            part_col = st.selectbox("Part column", raw_df.columns)
            operator_col = st.selectbox("Operator column", raw_df.columns)

            possible_factors = [
                col for col in raw_df.columns
                if col not in [value_col, part_col, operator_col]
            ]

            additional_factors = st.multiselect(
                "Additional factor columns",
                possible_factors,
            )

            all_factors = [part_col, operator_col] + additional_factors

            st.subheader("Factor Settings")

            factor_settings = {}

            for factor in all_factors:
                st.markdown(f"**{factor}**")

                col1, col2, col3 = st.columns(3)

                with col1:
                    kind = st.selectbox(
                        "Effect type",
                        ["random", "fixed"],
                        key=f"{factor}_kind",
                    )

                with col2:
                    default_role = (
                        "part_to_part"
                        if factor == part_col
                        else "reproducibility"
                    )

                    role_options = [
                        "part_to_part",
                        "reproducibility",
                        "ignore",
                    ]

                    role = st.selectbox(
                        "Gage R&R role",
                        role_options,
                        index=role_options.index(default_role),
                        key=f"{factor}_role",
                    )

                with col3:
                    st.metric("Levels", raw_df[factor].nunique())

                factor_settings[factor] = {
                    "kind": kind,
                    "role": role,
                }

            interaction_order = st.selectbox(
                "Maximum interaction order",
                [1, 2],
                index=1,
            )

            part_to_part_terms = st.multiselect(
                "Terms used for Part-to-Part variation",
                all_factors,
                default=[part_col],
            )

            with st.expander("Expanded Study Spec Preview"):
                st.json(
                    {
                        "value_col": value_col,
                        "part_col": part_col,
                        "operator_col": operator_col,
                        "factors": factor_settings,
                        "interaction_order": interaction_order,
                        "part_to_part_terms": part_to_part_terms,
                    }
                )

            if st.button("Run Expanded Gage R&R"):
                st.warning(
                    "ComputeExpandedGageRR is not connected yet. "
                    "Once compute_expanded.py exists, this button can run the expanded model."
                )

    except Exception as e:
        st.error(f"Error processing the file: {e}")
