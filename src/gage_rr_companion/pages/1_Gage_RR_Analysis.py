import streamlit as st
import pandas as pd

from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.compute_nested import ComputeGageRR_Nested
from gage_rr_companion.compute_type1 import compute_type1, generate_type1_run_chart
from gage_rr_companion.gage_rr_io import load_gage_rr_data
from gage_rr_companion.interpret_gage_rr import interpret_gage_rr
from gage_rr_companion.generateplots import generateplots


st.set_page_config(page_title="Gage R&R Companion", layout="wide")

st.title("Gage R&R Analysis")
st.write("Upload a CSV file and select the type of Gage study to run.")

uploaded_file = st.file_uploader("Upload your data CSV", type="csv")

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


def display_standard_gage_results(df, results):
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
        st.markdown(f"**Recommendation**  \n{interpretation['recommendation']}")

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


def display_type1_results(results, control_chart_df):
    """Display Type 1 Gage Study output."""

    st.subheader("Type 1 Gage Study Results")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean", f"{results['X_bar']:.4f}")
    col2.metric("Std Dev", f"{results['S']:.4f}")
    col3.metric("Study Variation", f"{results['SV']:.4f}")
    col4.metric("Bias", f"{results['Bias']:.4f}")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("t Statistic", f"{results['t_stat']:.4f}")
    col6.metric("p-value", f"{results['p_value']:.4f}")
    col7.metric("C_g", f"{results['C_g']:.4f}")
    col8.metric("C_gk", f"{results['C_gk']:.4f}")

    col9, col10 = st.columns(2)
    col9.metric(
        "% Var Repeatability",
        f"{results['%Var (Repeatability)']:.2f}%",
    )
    col10.metric(
        "% Var Repeatability + Bias",
        f"{results['%Var (Repeatability + Bias)']:.2f}%",
    )

    st.subheader("Plots")
    try:
        st.altair_chart(
            generate_type1_run_chart(control_chart_df),
            use_container_width=True,
        )
    except Exception as plot_error:
        st.warning(f"Type 1 run chart could not be generated: {plot_error}")

    with st.expander("Detailed Results", expanded=False):
        st.dataframe(pd.DataFrame([results]), use_container_width=True)

    with st.expander("Control Chart Data", expanded=False):
        st.dataframe(control_chart_df, use_container_width=True)


if uploaded_file is not None:
    try:
        if study_type in ["Crossed Gage R&R", "Nested Gage R&R"]:
            with st.spinner(f"Running {study_type} analysis..."):
                df = load_gage_rr_data(uploaded_file, is_path=False)

                if study_type == "Crossed Gage R&R":
                    results = ComputeGageRR(df)
                else:
                    results = ComputeGageRR_Nested(df)

            display_standard_gage_results(df, results)

        elif study_type == "Type 1 Gage Study":
            raw_df = pd.read_csv(uploaded_file)

            st.subheader("Type 1 Study Inputs")

            measurement_col = st.selectbox(
                "Measurement column",
                raw_df.columns,
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
            tolerance = st.number_input(
                "Total tolerance",
                value=1.0,
                min_value=0.000001,
                help="The total allowable tolerance for the measurement system, calculated as USL minus LSL.",
            )
            k = st.number_input(
                "K percent",
                value=20.0,
                min_value=0.000001,
                help="The percent of tolerance considered acceptable for measurement system variation. The default is 20%.",
            )

            if st.button("Run Type 1 Gage Study"):
                with st.spinner("Running Type 1 Gage Study..."):
                    type1_data = raw_df[[measurement_col]].copy()

                    results, control_chart_df = compute_type1(
                        study_name=study_name,
                        user=user,
                        X_m=x_m,
                        units=units,
                        tolerance=tolerance,
                        data=type1_data,
                        K=k,
                    )

                display_type1_results(results, control_chart_df)

        elif study_type == "Expanded Gage R&R":
            raw_df = pd.read_csv(uploaded_file)

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
