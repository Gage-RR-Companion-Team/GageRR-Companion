import streamlit as st
from gage_rr_companion.ui.sidebar import render_sidebar


st.set_page_config(
    page_title="Gage R&R Companion",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    .hero {
        padding: 2.2rem 2.5rem;
        border-radius: 24px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #334155 100%);
        color: white;
        margin-bottom: 2rem;
    }

    .hero h1 {
        font-size: 3rem;
        margin-bottom: 0.4rem;
    }

    .hero p {
        font-size: 1.15rem;
        color: #cbd5e1;
        max-width: 760px;
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
        color: #0f172a;
    }

    .card {
        padding: 1.25rem;
        border-radius: 18px;
        border: 1px solid #e5e7eb;
        background-color: #ffffff;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
        height: 100%;
    }

    .card h3 {
        margin-top: 0;
        margin-bottom: 0.4rem;
        color: #0f172a;
    }

    .card p, .card li {
        color: #475569;
        font-size: 0.95rem;
    }

    .badge {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }

    .supported {
        background-color: #dcfce7;
        color: #166534;
    }

    .assistant-badge {
        background-color: #dbeafe;
        color: #1d4ed8;
    }

    .workflow-step {
        padding: 1rem;
        border-left: 4px solid #2563eb;
        background-color: #f8fafc;
        border-radius: 12px;
        margin-bottom: 0.75rem;
    }

    .small-muted {
        color: #64748b;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

render_sidebar("home")

st.markdown(
    """
    <div class="hero">
        <h1>Gage R&R Companion</h1>
        <p>
            A guided measurement system analysis tool for engineers, technicians,
            and quality teams who need fast, clear, and interpretable Gage R&R results.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_a, col_b, col_c = st.columns([1.2, 1.2, 2])

with col_a:
    if st.button("Start Analysis", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Gage_RR_Analysis.py")

with col_b:
    if st.button("View Documentation", use_container_width=True):
        st.switch_page("pages/2_Documentation.py")

with col_c:
    st.markdown(
        """
        <p class="small-muted">
            Upload a formatted CSV, select a study type, and review metrics, plots, and interpretation.
        </p>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='section-title'>Supported Study Types</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        """
        <div class="card">
            <span class="badge supported">Supported</span>
            <h3>Crossed</h3>
            <p>Best when every operator measures every part multiple times.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div class="card">
            <span class="badge supported">Supported</span>
            <h3>Nested</h3>
            <p>Used when parts are unique to each operator or cannot be remeasured.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div class="card">
            <span class="badge supported">Supported</span>
            <h3>Type 1</h3>
            <p>Evaluates basic gage bias and repeatability using one reference part.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        """
        <div class="card">
            <span class="badge supported">Supported</span>
            <h3>Expanded</h3>
            <p>Includes additional sources of variation such as fixture, site, or condition.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='section-title'>Workflow</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([1.1, 1])

with left:
    st.markdown(
        """
        <div class="workflow-step">
            <b>1. Upload your dataset</b><br>
            Import a formatted CSV containing operators, parts, trials, and measurements.
        </div>

        <div class="workflow-step">
            <b>2. Select the study type</b><br>
            Choose the analysis method that matches your measurement study design.
        </div>

        <div class="workflow-step">
            <b>3. Review results</b><br>
            View variance components, ANOVA results, summary metrics, plots, and interpretation.
        </div>

        <div class="workflow-step">
            <b>4. Investigate root causes</b><br>
            Use visualizations and interpretation guidance to identify measurement system issues.
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        """
        <div class="card">
            <h3>Required CSV Format</h3>
            <p>Your dataset should include the required columns for the selected study type.</p>
            <p><b>Typical crossed study format:</b></p>
            <ul>
                <li>Operator</li>
                <li>Part</li>
                <li>Trial</li>
                <li>Measurement</li>
            </ul>
            <p class="small-muted">
                Additional study types may require reference values, appraiser groups,
                or nested part identifiers.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='section-title'>What This Tool Provides</div>",
    unsafe_allow_html=True,
)

f1, f2, f3 = st.columns(3)

with f1:
    st.markdown(
        """
        <div class="card">
            <h3>Statistical Output</h3>
            <p>
                ANOVA tables, variance components, repeatability,
                reproducibility, and part-to-part variation.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with f2:
    st.markdown(
        """
        <div class="card">
            <h3>Visual Diagnostics</h3>
            <p>
                Control charts, operator comparisons, measurement distributions,
                and contribution plots.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with f3:
    st.markdown(
        """
        <div class="card">
            <h3>Plain-English Interpretation</h3>
            <p>
                Summaries that help explain whether the measurement system
                is acceptable and what may need improvement.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='section-title'>Meet Cornelius</div>",
    unsafe_allow_html=True,
)

cornelius_left, cornelius_right = st.columns([1.15, 1])

with cornelius_left:
    st.markdown(
        """
        <div class="card">
            <span class="badge assistant-badge">Study Development Assistant</span>
            <h3>Cornelius helps users build better Gage R&amp;R studies</h3>
            <p>Cornelius is an integrated assistant designed to help guide users through the planning and development of Gage R&amp;R studies.</p>
            <p>Instead of only analyzing finished datasets, Cornelius helps users understand how to structure a study properly before data collection begins.</p>
            <p>This includes selecting study types, determining operators and parts, understanding balanced study design, and identifying potential issues before running the experiment.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with cornelius_right:
    st.markdown(
        """
        <div class="card">
            <h3>What Cornelius can help with</h3>
            <ul>
                <li>Selecting the appropriate study type</li>
                <li>Determining the number of operators and parts</li>
                <li>Understanding balanced vs. unbalanced studies</li>
                <li>Planning repeat measurements and trials</li>
                <li>Explaining study assumptions</li>
                <li>Helping structure CSV input data</li>
                <li>Identifying common study design mistakes</li>
                <li>Guiding users through workflow setup</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="card" style="margin-top: 1rem;">
        <h3>Why Cornelius matters</h3>
        <p>Many Gage R&amp;R issues originate during study planning rather than during statistical analysis. Poor part selection, insufficient trials, operator imbalance, and incorrect study structure can lead to misleading conclusions even if the calculations themselves are correct.</p>
        <p>Cornelius is designed to help users avoid these problems early and build more reliable measurement system studies from the start.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

st.markdown(
    """
    <p class="small-muted">
        Gage R&R Companion is intended to support measurement system analysis and engineering review.
        It does not replace formal quality approval in regulated environments.
    </p>
    """,
    unsafe_allow_html=True,
)