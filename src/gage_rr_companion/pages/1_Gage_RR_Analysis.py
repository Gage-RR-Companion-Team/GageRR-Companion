import json
import math
import os

import pandas as pd
import streamlit as st

try:
    from gage_rr_companion.ui.sidebar import render_sidebar
except Exception:
    def render_sidebar(active_page: str = ""):
        st.sidebar.markdown("## Gage R&R Companion")
        st.sidebar.caption("Measurement system analysis platform")

from gage_rr_companion.cornelius import call_agent, get_agent_backend, load_ai_secrets
from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.compute_nested import ComputeGageRR_Nested
from gage_rr_companion.compute_type1 import compute_type1, generate_type1_run_chart
from gage_rr_companion.gage_rr_io import (
    clean_uploaded_template_table,
    load_gage_rr_data,
    load_uploaded_table,
)
from gage_rr_companion.generateplots import generateplots
from gage_rr_companion.interpret_gage_rr import interpret_gage_rr


st.set_page_config(
    page_title="Gage R&R Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_ai_secrets()
render_sidebar("analysis")


def inject_css():
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        h1, h2, h3, h4 {
            letter-spacing: -0.02em;
        }

        h1 {
            font-weight: 800;
        }

        h2 {
            font-weight: 750;
        }

        h3 {
            font-weight: 700;
        }

        p {
            line-height: 1.65;
        }

        [data-testid="stMarkdownContainer"] p {
            font-size: 0.98rem;
        }

        .page-hero {
            padding: 2rem 2.25rem;
            border-radius: 24px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 65%, #334155 100%);
            color: white;
            margin-bottom: 1.5rem;
        }

        .page-hero h1 {
            font-size: 2.6rem;
            margin-bottom: 0.35rem;
            color: white;
        }

        .page-hero p {
            font-size: 1.05rem;
            color: #cbd5e1;
            max-width: 850px;
        }

        .section-title {
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            margin-top: 3rem;
            margin-bottom: 0.85rem;
            color: #0f172a;
        }

        .metric-card {
            padding: 1.15rem;
            border-radius: 18px;
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
            height: 100%;
        }

        .metric-card h4 {
            margin: 0 0 0.35rem 0;
            color: #475569;
            font-size: 0.9rem;
        }

        .metric-card h2 {
            margin: 0;
            color: #0f172a;
            font-size: 2.35rem;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .metric-card p {
            margin: 0.45rem 0 0 0;
            color: #64748b;
            font-size: 0.9rem;
        }

        .soft-card {
            padding: 1.25rem;
            border-radius: 18px;
            border: 1px solid #e5e7eb;
            background-color: #ffffff;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
            height: 100%;
            margin-bottom: 1rem;
        }

        .soft-card h3 {
            margin-top: 0;
            color: #0f172a;
        }

        .soft-card p,
        .soft-card li {
            color: #475569;
            font-size: 0.95rem;
        }

        .small-muted {
            color: #64748b;
            font-size: 0.88rem;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str):
    st.markdown(f"<div class='section-title'>{text}</div>", unsafe_allow_html=True)


def metric_card(label: str, value: str, note: str = ""):
    st.markdown(
        f"""
        <div class="metric-card">
            <h4>{label}</h4>
            <h2>{value}</h2>
            <p>{note}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def safe_pct(metrics: dict, key: str) -> str:
    value = metrics.get(key, None)
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def format_metric(value, suffix: str = "", digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)) and not math.isfinite(value):
        return "Not meaningful"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}{suffix}"
    return str(value)


def validate_dataset_preview(df: pd.DataFrame):
    section_title("Dataset Review")

    row_count = len(df)
    col_count = len(df.columns)
    missing_cells = int(df.isna().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Rows", f"{row_count:,}", "Total records detected")
    with c2:
        metric_card("Columns", f"{col_count:,}", "Dataset fields")
    with c3:
        metric_card("Missing Cells", f"{missing_cells:,}", "Should be reviewed before analysis")
    with c4:
        metric_card("Duplicate Rows", f"{duplicate_rows:,}", "May indicate repeated entries")

    if missing_cells == 0 and duplicate_rows == 0:
        st.success("Dataset passed basic validation checks.")
    else:
        if missing_cells > 0:
            st.warning(f"Dataset contains {missing_cells} missing cell(s).")
        if duplicate_rows > 0:
            st.warning(f"Dataset contains {duplicate_rows} duplicate row(s).")

    with st.expander("Preview uploaded dataset", expanded=False):
        st.dataframe(df.head(25), use_container_width=True)


def apply_cornelius_runtime_settings() -> str:
    """Use chat-page GUI settings when they exist, then return the active backend."""
    backend = st.session_state.get("cornelius_backend", get_agent_backend())
    if backend == "auto":
        backend = "openai_compatible"

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
        'analysis. In the follow-up actions, call the device/process the '
        '"measurement system" instead of "gage".\n\n'
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


def display_plot_card(title: str, chart, interpretation: str):
    left, right = st.columns([1.35, 0.85])

    with left:
        with st.container(border=True):
            st.subheader(title)
            st.altair_chart(chart, use_container_width=True)

    with right:
        with st.container(border=True):
            st.subheader("How to read this")
            st.write(interpretation)


def build_markdown_report(results, interpretation, study_type="Gage R&R Study"):
    metrics = results.get("summary_metrics", {})

    report = f"""# {study_type} Report

## Executive Summary

**Overall Status:**  
{interpretation.get("overall_status", "N/A")}

**Gage R&R Status:**  
{interpretation.get("gage_rr_status", "N/A")}

**Root Cause:**  
{interpretation.get("root_cause", "N/A")}

**Discrimination:**  
{interpretation.get("discrimination", "N/A")}

**Recommendation:**  
{interpretation.get("recommendation", "N/A")}

---

## Key Metrics

| Metric | Value |
|---|---:|
| % Gage R&R | {metrics.get("PercentGageRR", "N/A")} |
| % Repeatability | {metrics.get("PercentRepeatability", "N/A")} |
| % Reproducibility | {metrics.get("PercentReproducibility", "N/A")} |
| % Part-to-Part | {metrics.get("PercentPartToPart", "N/A")} |
| C_g | {metrics.get("C_g", "N/A")} |
| C_gk | {metrics.get("C_gk", "N/A")} |
| Bias | {metrics.get("Bias", "N/A")} |
| p-value | {metrics.get("p_value", "N/A")} |

---

## Notes

This report was generated by Gage R&R Companion. Final quality decisions should be reviewed by qualified engineering or quality personnel.
"""
    return report


def build_csv_download(df):
    return df.to_csv(index=False).encode("utf-8")


def export_section(df, results, interpretation, study_type_name="Gage R&R Study"):
    section_title("Export & Next Steps")

    report_md = build_markdown_report(results, interpretation, study_type_name)
    report_bytes = report_md.encode("utf-8")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button(
            label="Download Markdown Report",
            data=report_bytes,
            file_name="gage_rr_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with c2:
        st.download_button(
            label="Download Cleaned Dataset",
            data=build_csv_download(df),
            file_name="gage_rr_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c3:
        summary_df = pd.DataFrame([results.get("summary_metrics", {})])
        st.download_button(
            label="Download Summary Metrics",
            data=build_csv_download(summary_df),
            file_name="gage_rr_summary_metrics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.container(border=True):
        st.subheader("Recommended Next Actions")
        st.markdown(
            """
            - Review whether the study design was balanced.
            - Check whether repeatability or reproducibility is the dominant issue.
            - Review operator technique if reproducibility is high.
            - Review fixture, method, or equipment consistency if repeatability is high.
            - Rerun the study after correcting obvious measurement process issues.
            """
        )


def display_standard_gage_results(
    df,
    results,
    study_type_name: str,
    measurement_context: dict | None = None,
):
    interpretation = interpret_gage_rr(results)
    metrics = results["summary_metrics"]

    st.session_state["last_gage_rr_df"] = df
    st.session_state["last_gage_rr_results"] = results
    st.session_state["last_gage_rr_interpretation"] = interpretation

    section_title("Executive Summary")

    overall_status = interpretation.get("overall_status", "No overall status available.")

    if "NOT acceptable" in overall_status:
        st.error(overall_status)
    elif "conditionally acceptable" in overall_status:
        st.warning(overall_status)
    else:
        st.success(overall_status)

    summary_left, summary_right = st.columns([1.1, 1])

    with summary_left:
        with st.container(border=True):
            st.subheader("Primary Result")
            st.write(interpretation.get("gage_rr_status", "N/A"))
            st.markdown("**Root cause:**")
            st.write(interpretation.get("root_cause", "N/A"))

    with summary_right:
        with st.container(border=True):
            st.subheader("Recommended Review")
            st.markdown("**Discrimination:**")
            st.write(interpretation.get("discrimination", "N/A"))

            with st.spinner("Cornelius is reviewing the results..."):
                followup = get_cornelius_followup(
                    study_type_name,
                    results,
                    interpretation,
                    measurement_context,
                )
            render_cornelius_followup(followup)

    section_title("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card(
            "% Gage R&R",
            safe_pct(metrics, "PercentGageRR"),
            "Overall measurement system variation",
        )
    with col2:
        metric_card(
            "% Repeatability",
            safe_pct(metrics, "PercentRepeatability"),
            "Equipment or within-operator variation",
        )
    with col3:
        metric_card(
            "% Reproducibility",
            safe_pct(metrics, "PercentReproducibility"),
            "Operator-to-operator variation",
        )
    with col4:
        metric_card(
            "% Part-to-Part",
            safe_pct(metrics, "PercentPartToPart"),
            "Variation explained by actual parts",
        )

    section_title("Visual Diagnostics")

    try:
        plots = generateplots(df, results)

        diagnostic_tabs = st.tabs(
            [
                "Control Charts",
                "Operator Effects",
                "Variance Breakdown",
                "All Plots",
            ]
        )

        with diagnostic_tabs[0]:
            display_plot_card(
                "X-bar Control Chart",
                plots["xbar_control_chart"],
                (
                    "The X-bar chart shows whether part averages are separated enough "
                    "to detect real part-to-part variation. If most points are inside "
                    "the limits, the measurement system may not be distinguishing parts well."
                ),
            )

            display_plot_card(
                "R Control Chart",
                plots["r_control_chart"],
                (
                    "The R chart shows within-operator measurement consistency. Large ranges "
                    "or points outside control limits suggest repeatability problems."
                ),
            )

        with diagnostic_tabs[1]:
            display_plot_card(
                "Operator Comparison",
                plots["operator_boxplot"],
                (
                    "This plot compares measurement distributions by operator. Large shifts "
                    "between operators suggest reproducibility issues or differences in technique."
                ),
            )

        with diagnostic_tabs[2]:
            display_plot_card(
                "Variance Contribution",
                plots["variance_histogram"],
                (
                    "This chart shows where the total variation is coming from. A professional "
                    "measurement system should have most variation coming from part-to-part differences, "
                    "not the measurement system itself."
                ),
            )

        with diagnostic_tabs[3]:
            plot_col1, plot_col2 = st.columns(2)

            with plot_col1:
                with st.container(border=True):
                    st.subheader("X-bar Control Chart")
                    st.altair_chart(plots["xbar_control_chart"], use_container_width=True)

                with st.container(border=True):
                    st.subheader("Operator Comparison")
                    st.altair_chart(plots["operator_boxplot"], use_container_width=True)

            with plot_col2:
                with st.container(border=True):
                    st.subheader("R Control Chart")
                    st.altair_chart(plots["r_control_chart"], use_container_width=True)

                with st.container(border=True):
                    st.subheader("Variance Contribution")
                    st.altair_chart(plots["variance_histogram"], use_container_width=True)

    except Exception as plot_error:
        st.warning(f"Some plots could not be generated: {plot_error}")

    section_title("Detailed Results")

    result_tabs = st.tabs(
        [
            "Summary",
            "ANOVA",
            "Variance Components",
            "Gage R&R Table",
            "Operator Stats",
            "Warnings",
        ]
    )

    with result_tabs[0]:
        with st.container(border=True):
            st.subheader("Summary Metrics")
            st.dataframe(pd.DataFrame([metrics]), use_container_width=True)

    with result_tabs[1]:
        with st.container(border=True):
            st.subheader("ANOVA Table")
            if "anova_table" in results:
                st.dataframe(results["anova_table"], use_container_width=True)
            else:
                st.info("No ANOVA table available.")

    with result_tabs[2]:
        with st.container(border=True):
            st.subheader("Variance Components")
            st.dataframe(results["variance_components"], use_container_width=True)

    with result_tabs[3]:
        with st.container(border=True):
            st.subheader("Gage R&R Table")
            st.dataframe(results["gage_rr_table"], use_container_width=True)

    with result_tabs[4]:
        with st.container(border=True):
            st.subheader("Operator Statistics")
            st.dataframe(results["operator_stats"], use_container_width=True)

    with result_tabs[5]:
        with st.container(border=True):
            st.subheader("Warnings")
            warnings = results.get("warnings", [])

            if warnings:
                for warning in warnings:
                    st.warning(warning)
            else:
                st.success("No warnings detected.")

    with st.expander("Show raw result metadata", expanded=False):
        st.json(results.get("metadata", {}))

    export_section(df, results, interpretation, study_type_name)


def display_type1_results(results, control_chart_df, measurement_name: str):
    interpretation = interpret_type1_results(results)

    type1_payload = type1_results_for_cornelius(results, measurement_name)

    st.session_state["last_gage_rr_results"] = type1_payload
    st.session_state["last_gage_rr_interpretation"] = interpretation

    section_title("Executive Summary")

    overall_status = interpretation.get("overall_status", "No overall status available.")

    if "NOT acceptable" in overall_status:
        st.error(overall_status)
    elif "conditionally acceptable" in overall_status:
        st.warning(overall_status)
    else:
        st.success(overall_status)

    summary_left, summary_right = st.columns([1.1, 1])

    with summary_left:
        with st.container(border=True):
            st.subheader("Primary Result")
            st.write(interpretation.get("gage_rr_status", "N/A"))
            st.markdown("**Bias check:**")
            st.write(interpretation.get("discrimination", "N/A"))
            st.markdown("**Root cause:**")
            st.write(interpretation.get("root_cause", "N/A"))

    with summary_right:
        with st.container(border=True):
            with st.spinner("Cornelius is reviewing the results..."):
                followup = get_cornelius_followup(
                    "Type 1 Gage Study",
                    type1_payload,
                    interpretation,
                    {
                        "measurement_name": measurement_name,
                        "units": results["Units"],
                    },
                )
            render_cornelius_followup(followup)

    section_title("Key Metrics")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("C_g", format_metric(results["C_g"]), "Repeatability capability")
    with c2:
        metric_card("C_gk", format_metric(results["C_gk"]), "Repeatability with bias")
    with c3:
        metric_card("Bias", format_metric(results["Bias"]), "Difference from reference")
    with c4:
        metric_card("p-value", format_metric(results["p_value"]), "Bias significance")

    c5, c6 = st.columns(2)
    with c5:
        metric_card(
            "% Var Repeatability",
            format_metric(results["%Var (Repeatability)"], "%", digits=2),
            "Variation from repeatability",
        )
    with c6:
        metric_card(
            "% Var Repeatability + Bias",
            format_metric(results["%Var (Repeatability + Bias)"], "%", digits=2),
            "Combined repeatability and bias contribution",
        )

    section_title("Visual Diagnostics")

    try:
        with st.container(border=True):
            st.subheader("Type 1 Run Chart")
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

    section_title("Advanced Statistical Output")

    with st.expander("Show detailed Type 1 results", expanded=False):
        st.dataframe(pd.DataFrame([results]), use_container_width=True)

    with st.expander("Show control chart data", expanded=False):
        st.dataframe(control_chart_df, use_container_width=True)

    export_section(
        pd.DataFrame(control_chart_df),
        type1_payload,
        interpretation,
        "Type 1 Gage Study",
    )


inject_css()

st.markdown(
    """
    <div class="page-hero">
        <h1>Gage R&amp;R Analysis</h1>
        <p>Upload a measurement study dataset, choose the study design, and review the results through a guided dashboard.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

setup_left, setup_right = st.columns([1.2, 1])

with setup_left:
    uploaded_file = st.file_uploader(
        "Upload your data file",
        type=["csv", "xlsx", "xlsm", "xls"],
    )

with setup_right:
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
    label="Need help with formatting? Open the documentation page.",
)

if uploaded_file is None:
    section_title("Before You Begin")
    st.markdown(
        """
        <div class="soft-card">
            <h3>Upload a CSV or Excel file to begin</h3>
            <p>The analysis dashboard will appear after a dataset is uploaded. The app will first show a dataset review, then run the selected Gage R&amp;R workflow.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

try:
    raw_df = clean_uploaded_template_table(
        load_uploaded_table(uploaded_file, is_path=False)
    )
    validate_dataset_preview(raw_df)
    uploaded_file.seek(0)

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

        display_standard_gage_results(
            df,
            results,
            study_type,
            measurement_context,
        )

    elif study_type == "Type 1 Gage Study":
        section_title("Type 1 Study Setup")

        measurement_options = [
            column
            for column in raw_df.columns
            if str(column).strip().lower() not in {"test #", "test#", "test number"}
        ]
        if not measurement_options:
            raise ValueError("Type 1 data must include a measurement column.")

        with st.container(border=True):
            measurement_col = st.selectbox(
                "Measurement column",
                measurement_options,
                help=(
                    "The single column of repeated measurements from one operator. "
                    "Type 1 studies should ideally use more than 25 repeated measurements."
                ),
            )

            c1, c2 = st.columns(2)

            with c1:
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

            with c2:
                x_m = st.number_input(
                    "Measurement standard value (X_m)",
                    value=0.0,
                    help="The known reference or true value of the reliable calibration or validated standard.",
                )

                tolerance_unit_label = (
                    f"+/- {units.strip()}" if units.strip() else "+/- units"
                )
                tolerance_mode_options = {
                    tolerance_unit_label: "+/- units",
                    "+/- percent": "+/- percent",
                }

                tolerance_half_width = st.number_input(
                    "Tolerance (+/-)",
                    value=1.0,
                    min_value=0.000001,
                    help=(
                        "For +/- units, enter the allowed absolute difference from the standard. "
                        "For +/- percent, enter the percent of the standard value."
                    ),
                )
                tolerance_mode_label = st.selectbox(
                    "Tolerance format",
                    list(tolerance_mode_options),
                    help=(
                        "Enter the one-sided tolerance around the standard value. "
                        "The app converts it to total tolerance for the Type 1 calculation."
                    ),
                )
                tolerance_mode = tolerance_mode_options[tolerance_mode_label]

        if st.button("Run Type 1 Gage Study", type="primary"):
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
        section_title("Expanded Gage R&R Setup")

        st.info(
            "Expanded Gage R&R setup UI is available, but the compute engine "
            "must be connected after compute_expanded.py is implemented."
        )

        with st.container(border=True):
            c1, c2, c3 = st.columns(3)

            with c1:
                value_col = st.selectbox("Measurement column", raw_df.columns)

            with c2:
                part_col = st.selectbox("Part column", raw_df.columns)

            with c3:
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

        section_title("Factor Settings")

        factor_settings = {}

        for factor in all_factors:
            with st.container(border=True):
                st.markdown(f"### {factor}")

                col1, col2, col3 = st.columns(3)

                with col1:
                    kind = st.selectbox(
                        "Effect type",
                        ["random", "fixed"],
                        key=f"{factor}_kind",
                    )

                with col2:
                    default_role = (
                        "part_to_part" if factor == part_col else "reproducibility"
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
                    metric_card("Levels", f"{raw_df[factor].nunique()}", "Unique values")

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

        with st.expander("Expanded Study Spec Preview", expanded=False):
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

        if st.button("Run Expanded Gage R&R", type="primary"):
            st.warning(
                "ComputeExpandedGageRR is not connected yet. "
                "Once compute_expanded.py exists, this button can run the expanded model."
            )

except Exception as e:
    st.error(f"Error processing the file: {e}")
