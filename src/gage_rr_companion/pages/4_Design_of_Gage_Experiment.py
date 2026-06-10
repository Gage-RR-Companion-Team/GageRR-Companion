import streamlit as st

from gage_rr_companion.ui.sidebar import render_sidebar
from gage_rr_companion.cornelius import call_agent, generate_template, load_ai_secrets
from gage_rr_companion.doe_workflow import (
    STUDY_LABELS,
    STUDY_PLAIN_LABELS,
    guided_step_states,
    recommend_guided_study,
    template_help,
)


st.set_page_config(
    page_title="Design of Gage Experiment",
    page_icon="D",
    layout="wide",
    initial_sidebar_state="expanded",
)


FLOW_STYLES = """
<style>
.doe-rule { border-top: 1px solid #b8bcc5; margin: 1rem 0 1.4rem; }
.doe-mode-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-top: 1.2rem;
}
.doe-mode-card {
    border: 1px solid #d0d3da;
    border-radius: 6px;
    padding: 1.35rem;
    min-height: 118px;
    background: #ffffff;
}
.doe-mode-card strong { display: block; font-size: 1.25rem; margin-bottom: 0.55rem; }
.doe-mode-card span { color: #5f6673; line-height: 1.35rem; }
.doe-chart-wrap {
    width: 100%;
    overflow-x: auto;
    padding-top: 1rem;
}
.doe-cornelius-box {
    border: 1.5px solid #111827;
    border-radius: 18px;
    min-height: 430px;
    padding: 1rem;
    background: #ffffff;
}
.doe-chat-log {
    min-height: 300px;
    max-height: 300px;
    overflow-y: auto;
    margin-bottom: 0.75rem;
}
.doe-chat-assistant, .doe-chat-user {
    margin-bottom: 0.7rem;
    line-height: 1.35rem;
}
.doe-chat-user { text-align: right; }
.doe-template-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(145px, 1fr));
    gap: 0.75rem;
    margin-top: 1rem;
}
.doe-card {
    border: 1px solid #d9dde4;
    border-radius: 6px;
    padding: 1rem;
    background: #ffffff;
}
@media (max-width: 900px) {
    .doe-mode-grid { grid-template-columns: 1fr; }
    .doe-template-grid { grid-template-columns: 1fr; }
}
</style>
"""


QUESTION_ONE = "Q1: Do you want to identify the repeatability of your process, or both the repeatability and reproducibility?"
QUESTION_TWO = "Q2: Is there more than one measurement factor you wish to evaluate?"
QUESTION_THREE = "Q3: Is this testing destructive?"


def set_answer(key: str, value) -> None:
    st.session_state[key] = value


def reset_guided_answers() -> None:
    for key in ["doe_scope", "doe_multiple_parameters", "doe_destructive"]:
        st.session_state.pop(key, None)


def change_mode(mode: str) -> None:
    st.session_state.doe_mode = mode
    reset_guided_answers()


def status_class(enabled: bool, active: bool = False) -> tuple[str, str, str]:
    if active:
        return "#d9d9d9", "#111111", "#111111"
    if enabled:
        return "#ffffff", "#b8bcc5", "#111111"
    return "#f5f5f5", "#d6d6d6", "#c5c8cf"


STUDY_BOX_COLORS = {
    "type1": "#a8ec7c",
    "crossed": "#f4e274",
    "nested": "#f4e274",
    "expanded": "#eb8686",
}


def study_box_style(study_type: str, recommendation_type: str | None, multiple_parameters: bool | None) -> tuple[str, str, str]:
    active = recommendation_type == study_type
    possible_expanded = study_type == "expanded" and bool(multiple_parameters)
    fill = STUDY_BOX_COLORS[study_type]
    if active or possible_expanded:
        return fill, "#111111", "#111111"
    return fill, "#d6d6d6", "#b7bbc4"


def svg_rect(x, y, w, h, rx, fill, stroke, text, color="#111111", weight="500") -> str:
    lines = text.split("|")
    first_y = y + h / 2 - (len(lines) - 1) * 10
    tspans = "".join(
        f'<tspan x="{x + w / 2}" y="{first_y + index * 22}">{line}</tspan>'
        for index, line in enumerate(lines)
    )
    return f"""
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.4" />
    <text text-anchor="middle" font-size="15" font-weight="{weight}" fill="{color}" font-family="Arial, sans-serif">{tspans}</text>
    """


def svg_line(x1, y1, x2, y2, active: bool) -> str:
    stroke = "#111827" if active else "#dddddd"
    width = "2.4" if active else "1.4"
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" />'


def render_guided_flowchart(states: dict[str, str], answers: dict[str, str | bool | None], recommendation) -> None:
    q1_active = states["q1"] == "active"
    q1_enabled = states["q1"] in {"active", "complete"}
    q2_enabled = states["q2"] in {"active", "complete"}
    q3_enabled = states["q3"] in {"active", "complete"}
    recommendation_type = recommendation.study_type
    multiple_parameters = answers.get("multiple_parameters")
    q1_fill, q1_stroke, q1_text = status_class(q1_enabled, q1_active)
    q2_fill, q2_stroke, q2_text = status_class(q2_enabled, states["q2"] == "active")
    q3_fill, q3_stroke, q3_text = status_class(q3_enabled, states["q3"] == "active")

    type1_fill, type1_stroke, type1_text = study_box_style("type1", recommendation_type, multiple_parameters)
    crossed_fill, crossed_stroke, crossed_text = study_box_style("crossed", recommendation_type, multiple_parameters)
    nested_fill, nested_stroke, nested_text = study_box_style("nested", recommendation_type, multiple_parameters)
    expanded_fill, expanded_stroke, expanded_text = study_box_style("expanded", recommendation_type, multiple_parameters)

    scope = answers.get("scope")
    multiple_parameters = answers.get("multiple_parameters")
    destructive = answers.get("destructive")
    q1_to_type1 = scope == "repeatability_only"
    q1_to_q2 = scope == "repeatability_reproducibility"
    q2_to_expanded = bool(multiple_parameters)
    q2_to_q3 = q1_to_q2 and multiple_parameters is not None
    q3_to_nested = destructive is True and not multiple_parameters
    q3_to_crossed = destructive is False and not multiple_parameters

    svg = f"""
    <div class="doe-chart-wrap">
    <svg viewBox="0 0 760 410" width="100%" height="410" role="img" aria-label="Guided Gage experiment flowchart">
        {svg_line(80, 176, 205, 176, q1_to_q2)}
        {svg_line(80, 136, 80, 68, q1_to_type1)}
        {svg_line(80, 68, 565, 68, q1_to_type1)}
        {svg_line(288, 176, 365, 176, q2_to_q3)}
        {svg_line(247, 206, 247, 350, q2_to_expanded)}
        {svg_line(247, 350, 565, 350, q2_to_expanded)}
        {svg_line(448, 176, 565, 176, q3_to_crossed)}
        {svg_line(407, 206, 407, 256, q3_to_nested)}
        {svg_line(407, 256, 565, 256, q3_to_nested)}
        {svg_rect(38, 136, 84, 80, 16, q1_fill, q1_stroke, "Q1", q1_text)}
        {svg_rect(205, 146, 84, 60, 16, q2_fill, q2_stroke, "Q2", q2_text)}
        {svg_rect(365, 146, 84, 60, 16, q3_fill, q3_stroke, "Q3", q3_text)}
        {svg_rect(565, 24, 138, 88, 16, type1_fill, type1_stroke, "Type-1|Testing", type1_text)}
        {svg_rect(565, 118, 138, 88, 16, crossed_fill, crossed_stroke, "Crossed|Gage R&R", crossed_text)}
        {svg_rect(565, 212, 138, 88, 16, nested_fill, nested_stroke, "Nested|Gage R&R", nested_text)}
        {svg_rect(565, 306, 138, 88, 16, expanded_fill, expanded_stroke, "Expanded|Gage R&R", expanded_text)}
    </svg>
    </div>
    """
    st.markdown(svg, unsafe_allow_html=True)


def render_template_button(
    study_type: str,
    key: str,
    measurement_name: str | None = None,
    *,
    row_count: int | None = None,
    num_operators: int | None = None,
    num_parts: int | None = None,
    num_trials: int | None = None,
    parameter_names: list[str] | None = None,
) -> None:
    filename, excel_bytes = generate_template(
        study_type,
        measurement_name,
        row_count=row_count,
        num_operators=num_operators,
        num_parts=num_parts,
        num_trials=num_trials,
        parameter_names=parameter_names,
    )
    st.download_button(
        "Generate Template",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
        use_container_width=True,
    )
    st.caption(template_help(study_type))


def expanded_parameter_names(prefix: str) -> list[str]:
    count = int(st.session_state.get(f"{prefix}_parameter_count", 1))
    names = []
    for index in range(1, count + 1):
        default_name = f"Parameter {index}"
        names.append(st.session_state.get(f"{prefix}_parameter_{index}", default_name))
    return names


def render_expanded_template_controls(prefix: str) -> dict:
    st.caption(
        "Expanded templates include Part, Operator, Trial, Value, and editable parameter columns "
        "for extra factors such as station, fixture, probe, method, site, or batch."
    )
    cols = st.columns(3)
    with cols[0]:
        num_operators = st.number_input(
            "Operators/appraisers",
            min_value=1,
            value=3,
            key=f"{prefix}_operators",
        )
    with cols[1]:
        num_parts = st.number_input(
            "Parts",
            min_value=1,
            value=10,
            key=f"{prefix}_parts",
        )
    with cols[2]:
        num_trials = st.number_input(
            "Replicates/trials per part",
            min_value=1,
            value=3,
            key=f"{prefix}_trials",
        )
    st.number_input(
        "Number of parameters",
        min_value=1,
        max_value=8,
        value=1,
        step=1,
        key=f"{prefix}_parameter_count",
    )
    parameter_count = int(st.session_state.get(f"{prefix}_parameter_count", 1))
    for index in range(1, parameter_count + 1):
        st.text_input(
            f"Parameter {index} header",
            value=st.session_state.get(f"{prefix}_parameter_{index}", f"Parameter {index}"),
            key=f"{prefix}_parameter_{index}",
        )
    estimated_rows = int(num_operators) * int(num_parts) * int(num_trials) * parameter_count
    st.caption(f"Template will generate {estimated_rows:,} data rows plus the example row.")
    return {
        "num_operators": num_operators,
        "num_parts": num_parts,
        "num_trials": num_trials,
        "parameter_names": expanded_parameter_names(prefix),
    }


def render_cornelius_panel(context: str) -> None:
    messages_key = f"cornelius_{context}_messages"
    if messages_key not in st.session_state:
        st.session_state[messages_key] = [
            {"role": "assistant", "content": "Hi, I am Cornelius."}
        ]

    with st.container(border=True):
        st.markdown("**Questions? Ask Cornelius!**")
        chat_area = st.container(height=300, border=False)
        with chat_area:
            for message in st.session_state[messages_key]:
                if message["role"] == "user":
                    st.markdown(f"**You:** {message['content']}")
                else:
                    st.markdown(f"**Cornelius:** {message['content']}")

        with st.form(f"cornelius_{context}_form", clear_on_submit=True):
            prompt = st.text_input(
                "Enter text here",
                key=f"cornelius_{context}_input",
                label_visibility="collapsed",
                placeholder="Enter text here",
            )
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and prompt.strip():
        st.session_state[messages_key].append({"role": "user", "content": prompt.strip()})
        with st.spinner("Cornelius is thinking..."):
            response = call_agent(prompt.strip(), history=st.session_state[messages_key])
        st.session_state[messages_key].append({"role": "assistant", "content": response})
        st.rerun()


def render_mode_picker() -> None:
    st.title("Design of Gage Experiment")
    st.caption("AI-assisted design of experiment for Gage testing.")
    st.markdown('<div class="doe-rule"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="doe-mode-grid">
            <div class="doe-mode-card"><strong>Guided</strong><span>Best if you want the app to walk you through the study choice.</span></div>
            <div class="doe-mode-card"><strong>Unguided</strong><span>Best if you already know the type of Gage study you need.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Guided", use_container_width=True, type="primary"):
            change_mode("Guided")
            st.rerun()
    with col2:
        if st.button("Unguided", use_container_width=True):
            change_mode("Unguided")
            st.rerun()


def render_guided() -> None:
    if st.button("Back to Guided / Unguided", key="guided_back"):
        st.session_state.pop("doe_mode", None)
        reset_guided_answers()
        st.rerun()

    st.title("Guided")
    left, right = st.columns([2.35, 1], gap="large")

    with left:
        st.header("Design of Gage Experiment:")
        st.subheader("AI Assisted design of experiment for Gage testing")
        st.markdown('<div class="doe-rule"></div>', unsafe_allow_html=True)

        st.markdown(f"**{QUESTION_ONE}**")
        q1_left, q1_right = st.columns([1, 1])
        with q1_left:
            if st.button("Repeatability", use_container_width=True):
                set_answer("doe_scope", "repeatability_only")
                st.session_state.pop("doe_multiple_parameters", None)
                st.session_state.pop("doe_destructive", None)
                st.rerun()
        with q1_right:
            if st.button("Repeatability and reproducibility", use_container_width=True):
                set_answer("doe_scope", "repeatability_reproducibility")
                st.rerun()

        scope = st.session_state.get("doe_scope")
        multiple_parameters = st.session_state.get("doe_multiple_parameters")
        destructive = st.session_state.get("doe_destructive")

        if scope == "repeatability_reproducibility":
            st.markdown(f"**{QUESTION_TWO}**")
            q2_one, q2_more = st.columns(2)
            with q2_one:
                if st.button("Only one measurement factor", use_container_width=True):
                    set_answer("doe_multiple_parameters", False)
                    st.rerun()
            with q2_more:
                if st.button("More than one measurement factor", use_container_width=True):
                    set_answer("doe_multiple_parameters", True)
                    st.rerun()

        if scope == "repeatability_reproducibility" and multiple_parameters is not None:
            st.markdown(f"**{QUESTION_THREE}**")
            q3_yes, q3_no = st.columns(2)
            with q3_yes:
                if st.button("Yes, it is destructive", use_container_width=True):
                    set_answer("doe_destructive", True)
                    st.rerun()
            with q3_no:
                if st.button("No, it is not destructive", use_container_width=True):
                    set_answer("doe_destructive", False)
                    st.rerun()

        answers = {
            "scope": scope,
            "multiple_parameters": multiple_parameters,
            "destructive": destructive,
        }
        states = guided_step_states(answers)
        recommendation = recommend_guided_study(answers)
        render_guided_flowchart(states, answers, recommendation)

        if recommendation.label:
            st.success(f"Recommended: {recommendation.label}")
            st.write(recommendation.reason)
            measurement_name = None
            template_kwargs = {}
            if recommendation.study_type == "type1":
                measurement_name = st.text_input(
                    "What are you measuring?",
                    placeholder="Thickness, viscosity, conductivity...",
                )
                template_kwargs["row_count"] = st.number_input(
                    "Template rows",
                    min_value=25,
                    value=50,
                    step=1,
                    key="guided_type1_template_rows",
                )
            elif recommendation.study_type in {"crossed", "nested"}:
                cols = st.columns(3)
                with cols[0]:
                    template_kwargs["num_operators"] = st.number_input(
                        "Operators/appraisers",
                        min_value=1,
                        value=3,
                        key="guided_template_operators",
                    )
                with cols[1]:
                    template_kwargs["num_parts"] = st.number_input(
                        "Parts per operator" if recommendation.study_type == "nested" else "Parts",
                        min_value=1,
                        value=10,
                        key="guided_template_parts",
                    )
                with cols[2]:
                    template_kwargs["num_trials"] = st.number_input(
                        "Trials per part",
                        min_value=1,
                        value=3,
                        key="guided_template_trials",
                    )
            if recommendation.study_type == "expanded":
                st.info("For an expanded study, start by focusing on the most important extra measurement-system factors.")
                template_kwargs.update(render_expanded_template_controls("guided_expanded_template"))
            render_template_button(
                recommendation.study_type,
                "guided_template",
                measurement_name,
                **template_kwargs,
            )
        else:
            st.info(recommendation.reason)

    with right:
        render_cornelius_panel("guided")


def render_unguided() -> None:
    if st.button("Back to Guided / Unguided", key="unguided_back"):
        st.session_state.pop("doe_mode", None)
        reset_guided_answers()
        st.rerun()

    st.title("Unguided")
    left, right = st.columns([2.35, 1], gap="large")

    with left:
        st.header("Design of Gage Experiment:")
        st.subheader("AI Assisted design of experiment for Gage testing")
        st.markdown('<div class="doe-rule"></div>', unsafe_allow_html=True)
        st.write(
            "The buttons below provide an empty Excel template with format compatible with the "
            "Gage R&R companion application. Click the button corresponding to your testing "
            "to download the Excel template corresponding to your testing."
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; font-weight:700;'>Generate Template:</div>", unsafe_allow_html=True)
        st.markdown('<div class="doe-rule" style="margin:0.7rem 0 1.5rem;"></div>', unsafe_allow_html=True)

        cols = st.columns(4)
        unguided_buttons = [
            ("type1", "Type-1 Testing"),
            ("crossed", "Crossed|Gage R&R"),
            ("nested", "Nested|Gage R&R"),
            ("expanded", "Expanded|Gage R&R"),
        ]
        for index, (study_type, label) in enumerate(unguided_buttons):
            with cols[index]:
                button_label = label.replace("|", " ")
                box_label = label.replace("|", "<br>")
                st.markdown(
                    f"""
                    <div style="
                        background:{STUDY_BOX_COLORS[study_type]};
                        border:1.5px solid #111111;
                        border-radius:14px;
                        min-height:86px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        text-align:center;
                        padding:0.6rem;
                        margin-bottom:0.65rem;
                    ">{box_label}</div>
                    """,
                    unsafe_allow_html=True,
                )
                template_kwargs = {}
                if study_type == "expanded":
                    template_kwargs = {
                        "parameter_names": ["Parameter 1"],
                    }
                filename, excel_bytes = generate_template(study_type, **template_kwargs)
                st.download_button(
                    button_label,
                    data=excel_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"unguided_{study_type}",
                    use_container_width=True,
                )
                if study_type == "expanded":
                    st.caption("Includes the core expanded-study columns from the notebook example. Add or rename factor columns as needed.")


    with right:
        render_cornelius_panel("unguided")


load_ai_secrets()
render_sidebar("design")
st.markdown(FLOW_STYLES, unsafe_allow_html=True)

mode = st.session_state.get("doe_mode")
if mode == "Guided":
    render_guided()
elif mode == "Unguided":
    render_unguided()
else:
    render_mode_picker()
