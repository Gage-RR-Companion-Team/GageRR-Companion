import streamlit as st

from gage_rr_companion.ui.sidebar import render_sidebar

st.set_page_config(
    page_title="Gage R&R Documentation",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar("documentation")

st.title("Gage R&R Documentation")
st.write("Brief documentation and resources for Gage R&R analysis.")
st.markdown(
    """
    ## 💻 What is the Gage R&R Companion?
    The Gage R&R Companion is a Streamlit application designed to help users to perform
    Gage Repeatability and Reproducibility (Gage R&R) analysis on their measurement system data.
    It provides an easy-to-use interface for uploading data, computing results, and interpreting the findings.

    ## ❔ What is Gage R&R Analysis?
    Gage Repeatability and Reproducibility (Gage R&R) is a statistical method used in measurement systems analysis (MSA) to detemrmine how much variation in your measurements comes form the measurement system itself rather than the actual parts being measured. Essentially, it answers:
    > "Can I trust my measurement process?"

    ## 🔑 Key Metrics
    - **% Gage R&R**: The percentage of total variation that is due to the measurement system. A lower percentage indicates a better measurement system.
    - **% Repeatability**: The percentage of total variation that is due to repeatability (variation when the same operator measures the same part multiple times).
    - **% Reproducibility**: The percentage of total variation that is due to reproducibility (variation when different operators measure the same part).
    - **% Part-to-Part**: The percentage of total variation that is due to actual differences between the parts being measured.

    ## 📊 Interpretation Guidelines
    - **% Gage R&R < 10%**: The measurement system is generally considered acceptable.
    - **10% ≤ % Gage R&R < 30%**: The measurement system may be conditionally acceptable, but improvement is recommended.
    - **% Gage R&R ≥ 30%**: The measurement system is not acceptable and requires improvement.  

    ## ▶️ Quick Start
    To begin Crossed or Nested analysis, upload the raw measurement readings from the study, not a calculated results table. The file should match the same structure as the generated templates:

    | Operator | Part | Trial | Value |
    |----------|----------|----------|----------|
    |  |  |  |

    All values must be filled for analysis to be successful. Do not include summary-result columns such as **% Gage R&R**, **% Study Var**, or **% Contribution** as required upload fields; the app calculates those after upload.

    When the CSV or Excel file is uploaded, analysis will begin immediately and results will be shown on the same page.

    ## 📌 Scope

    This program currently supports crossed Gage R&R studies utilizing ANOVA-based calculations.
    It is intended for balanced datasets, and does not replace formal review by a quality engineer in regulated settings.

    In the future, this program will provide more studies such as nested Gage R&R studies.

    ## 📚 Resources
    Additional resources for learning about Gage R&R analysis can be found below:
    - [ASQ Gage R&R Guide](https://asq.org/quality-resources/gage-repeatability?srsltid=AfmBOoqWP1c-bsj5TwBh-o1X-QN3fSPi8bCMTsaI1BenUD8FpZA1H4h0)
    - [Six Sigma](https://sixsigmastudyguide.com/gage-repeatability-and-reproducibility-rr/)
    """
)