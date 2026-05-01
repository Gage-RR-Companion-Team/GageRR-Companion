import streamlit as st
from gage_rr_companion.compute import ComputeGageRR
from gage_rr_companion.gage_rr_io import load_gage_rr_data
from gage_rr_companion.interpret_gage_rr import interpret_gage_rr
from gage_rr_companion.generateplots import generateplots

st.set_page_config(page_title="Gage R&R Companion", layout="wide")

st.title("Gage R&R Analysis")
st.write("Upload a CSV file to compute Gage R&R results.")

data = st.file_uploader("Upload your Gage R&R data (CSV format)", type="csv")
st.page_link("pages/2_Documentation.py", label="Need help with formatting? Check out the documentation page!")

if data is not None:
    try:
        with st.spinner("Running Gage R&R analysis..."):
            df = load_gage_rr_data(data, is_path=False)
            results = ComputeGageRR(df)
            interpretation = interpret_gage_rr(results)
            plots = generateplots(df, results)

        # -----------------------------
        # Summary Metrics
        # -----------------------------
        st.subheader("Summary Metrics")
        metrics = results["summary_metrics"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("% Gage R&R", f"{metrics['PercentGageRR']:.2f}%")
        col2.metric("% Repeatability", f"{metrics['PercentRepeatability']:.2f}%")
        col3.metric("% Reproducibility", f"{metrics['PercentReproducibility']:.2f}%")
        col4.metric("% Part-to-Part", f"{metrics['PercentPartToPart']:.2f}%")

        # -----------------------------
        # Interpretation
        # -----------------------------
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

        # -----------------------------
        # Plots
        # -----------------------------
        st.subheader("Plots")

        plot_col1, plot_col2 = st.columns(2)

        with plot_col1:
            st.altair_chart(plots["xbar_control_chart"], use_container_width=True)
            st.altair_chart(plots["operator_boxplot"], use_container_width=True)

        with plot_col2:
            st.altair_chart(plots["r_control_chart"], use_container_width=True)
            st.altair_chart(plots["variance_histogram"], use_container_width=True)

        # -----------------------------
        # Detailed Results
        # -----------------------------
        with st.expander("Detailed Results"):
            detail_tab1, detail_tab2, detail_tab3, detail_tab4 = st.tabs([
                "ANOVA Table",
                "Variance Components",
                "Gage R&R Table",
                "Operator Statistics"
            ])

            with detail_tab1:
                st.dataframe(results["anova_table"], use_container_width=True)

            with detail_tab2:
                st.dataframe(results["variance_components"], use_container_width=True)

            with detail_tab3:
                st.dataframe(results["gage_rr_table"], use_container_width=True)

            with detail_tab4:
                st.dataframe(results["operator_stats"], use_container_width=True)

    except Exception as e:
        st.error(f"Error processing the file: {e}")