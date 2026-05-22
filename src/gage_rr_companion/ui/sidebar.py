import streamlit as st


def render_sidebar(active_page: str = ""):
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }

        .sidebar-header {
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
        }

        .sidebar-title {
            font-size: 1.5rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0.2rem;
            letter-spacing: -0.03em;
        }

        .sidebar-subtitle {
            font-size: 0.92rem;
            color: #64748b;
        }

        .sidebar-section {
            margin-top: 2rem;
            margin-bottom: 0.75rem;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
        }

        .workflow-text {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.8;
        }

        [data-testid="stSidebarNav"] {
            margin-top: 0.5rem;
        }

        [data-testid="stSidebarNav"] ul {
            gap: 0.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <div class="sidebar-header">
            <div class="sidebar-title">Gage R&amp;R Companion</div>
            <div class="sidebar-subtitle">
                Measurement system analysis platform
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <div class="sidebar-section">Workflow</div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        """
        <div class="workflow-text">
        1. Upload Dataset<br>
        2. Select Study<br>
        3. Run Analysis<br>
        4. Review Results
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    st.sidebar.caption(
        "Built for engineering, manufacturing, and quality workflows."
    )