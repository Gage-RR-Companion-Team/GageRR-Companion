"""Pure-Python routing for Cornelius chat turns.

This module intentionally avoids Streamlit, Hugging Face, and network imports so
chat behavior can be tested locally.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Literal


RouterAction = Literal["ask_followup", "call_model", "generate_template", "redirect"]


@dataclass(frozen=True)
class RouterResult:
    action: RouterAction
    message: str
    updated_state: dict[str, Any] = field(default_factory=dict)
    template_type: str | None = None
    measurement_context: str | None = None

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


TEMPLATE_TYPES = {"type1", "nested", "crossed", "expanded"}

DIRECT_SCOPE_KEYWORDS = [
    "msa", "measurement system", "gage", "gauge", "g r&r", "g r and r",
    "r&r", "repeatability", "reproducibility", "ndc", "bias", "linearity",
    "stability", "type 1", "type1", "crossed", "nested", "operator",
    "appraiser", "part", "trial", "variance component", "anova",
    "template", "xlsx", "excel", "csv", "upload", "destructive",
    "non-destructive", "nondestructive", "non destructive", "calibration",
    "inspection", "measurement", "value", "readout", "conductivity", "probe",
    "pump", "flow rate", "flowrate", "membrane", "fixture", "method",
    "expanded", "why", "better", "sample", "electrode", "factor", "factors",
]

ADJACENT_SCOPE_KEYWORDS = [
    "quality", "six sigma", "asq", "aiag", "iso", "astm", "control chart",
    "capability", "cpk", "cp", "tolerance", "process variation",
    "standard deviation", "variance", "mean", "statistics", "confidence",
]

UNRELATED_TASK_PATTERNS = [
    "recipe", "cook", "bake", "meal plan", "shopping list",
    "write a story", "poem", "lyrics", "joke", "riddle",
    "travel itinerary", "stock pick", "dating advice",
]

FOLLOWUP_PATTERNS = [
    "yes", "yeah", "yep", "sure", "ok", "okay", "please", "make it", "do it",
    "continue", "that one", "the template", "make the template",
    "generate template", "generate the template", "make the file", "generate file",
    "create file", "download file", "what value", "which value",
    "what do i use", "which do i use", "do i input", "should i input",
    "what column", "which column", "what goes", "where do i put",
]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _history_has_scope(history: list[dict[str, Any]] | None) -> bool:
    if not history:
        return False
    recent = " ".join(
        message.get("content", "")
        for message in history[-6:]
        if isinstance(message, dict)
    ).lower()
    return _contains_any(recent, DIRECT_SCOPE_KEYWORDS + ADJACENT_SCOPE_KEYWORDS)


def classify_prompt_scope(query: str, history: list[dict[str, Any]] | None = None) -> str:
    text = query.lower().strip()
    if not text:
        return "ambiguous"
    if text in {"hi", "hello", "hey", "good morning", "good afternoon"}:
        return "direct"
    if _contains_any(text, UNRELATED_TASK_PATTERNS):
        return "out_of_scope"
    if _contains_any(text, DIRECT_SCOPE_KEYWORDS):
        return "direct"
    if _contains_any(text, ADJACENT_SCOPE_KEYWORDS):
        return "adjacent"
    if _history_has_scope(history) and (
        _contains_any(text, FOLLOWUP_PATTERNS) or "?" in text or len(text.split()) <= 12
    ):
        return "direct"
    if any(word in text for word in ["measure", "measuring", "data", "study", "test"]):
        return "ambiguous"
    return "out_of_scope"


def out_of_scope_response() -> str:
    return (
        "I am focused on Gage R&R and measurement-system analysis, so I cannot help "
        "much with that topic. If you are working on a measurement process, I can "
        "help choose a study type, build the upload template, or interpret your results."
    )


def ambiguous_scope_response() -> str:
    return (
        "Is this related to a measurement system or inspection process? If so, tell me "
        "what you are measuring and how the data will be collected."
    )


def detect_study_type(prompt: str) -> str | None:
    text = prompt.lower()
    if re.search(r"\btype\s*1\b|\btype1\b", text):
        return "type1"
    if "nested" in text:
        return "nested"
    if "crossed" in text or re.search(r"\bcross\b", text):
        return "crossed"
    return None


def detect_template_request(prompt: str) -> str | None:
    text = prompt.lower()
    wants_file = any(
        word in text
        for word in ["template", "excel", "spreadsheet", "xlsx", "download", "file"]
    )
    if not wants_file:
        return None
    if "expanded" in text:
        return "expanded"
    return detect_study_type(prompt) or "known"


def detect_recommended_study_type(content: str) -> str | None:
    text = content.lower()
    patterns = [
        r"study type:\s*(type\s*1|crossed|nested)",
        r"recommend(?:ation|ed)?:?\s*(type\s*1|crossed|nested)",
        r"(type\s*1|crossed|nested)\s+gage\s+r&r",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return detect_study_type(match.group(1))
    return None


def is_template_confirmation(prompt: str) -> bool:
    text = prompt.lower().strip()
    words = set(re.findall(r"[a-z0-9]+", text))
    confirmation = {"yes", "yeah", "yep", "sure", "please", "ok", "okay"}
    template_words = ["template", "excel", "xlsx", "spreadsheet", "file", "download"]
    generate_words = ["generate", "make", "create", "build", "export"]
    has_confirmation = bool(words & confirmation)
    has_template = any(word in text for word in template_words)
    has_generate = any(word in text for word in generate_words)
    if words and words <= confirmation:
        return True
    return (has_confirmation and (has_template or has_generate)) or (
        has_generate and has_template
    )


def detect_measurement_context(prompt: str) -> str | None:
    text = prompt.strip()
    patterns = [
        r"(?:measuring|measure|measurement(?:\s+is|\s+of)?|for)\s+([A-Za-z][A-Za-z0-9 /_-]{1,40})",
        r"(?:called|named)\s+([A-Za-z][A-Za-z0-9 /_-]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = re.split(r"[.?!,;]", match.group(1).strip())[0].strip()
            if value.lower() not in {"crossed", "nested", "type", "template", "excel"}:
                return value
    if len(text) <= 40 and "?" not in text and not detect_template_request(text) and not is_template_confirmation(text):
        if classify_prompt_scope(text) != "out_of_scope":
            return text
    return None


def template_followup_question(study_type: str | None, missing: list[str] | None = None) -> str:
    missing = missing or []
    if "study_type" in missing:
        return (
            "I can make that, but I need the study type first. Is this Type 1, "
            "Crossed, or Nested? If you are not sure, tell me whether the test is "
            "destructive and whether each operator can measure the same parts."
        )
    if "destructive_status" in missing:
        return (
            "Before I generate a template, is the measurement destructive or "
            "non-destructive, and can each operator measure the same parts?"
        )
    if study_type:
        return (
            "I can make that template. Before I export it, what measurement are you "
            "recording, such as length, diameter, torque, or conductivity?"
        )
    return (
        "I can make that, but I need the study type and measurement first. Is this "
        "Type 1, Crossed, or Nested, and what measured readout will go in the file?"
    )


def template_chat_response(study_type: str, measurement_context: str | None = None) -> str:
    labels = {"type1": "Type 1", "nested": "Nested", "crossed": "Crossed"}
    headers = {
        "type1": "Test #, <Measurement Name>",
        "nested": "Test #, Operator, Part, Trial, Value",
        "crossed": "Test #, Operator, Part, Trial, Value",
    }
    notes = {
        "type1": "Use one row per repeated measurement of the same reference part.",
        "nested": "Use one row per measurement; parts are nested within operator.",
        "crossed": "Use one row per measurement; every operator measures every part for each trial.",
    }
    measurement_note = (
        f"Measurement recorded: {measurement_context}.\n\n" if measurement_context else ""
    )
    return (
        f"I created the {labels[study_type]} Excel template for you.\n\n"
        f"{measurement_note}"
        f"Headers: `{headers[study_type]}`\n\n"
        f"{notes[study_type]} `Test #` is pre-populated for the planned run count "
        "and is ignored by the compute functions. The template is long format, so it "
        "does not use `Measurement 1`, `Measurement 2`, or other wide-format trial columns."
    )


def expanded_template_response(state: dict[str, Any]) -> str:
    factors = []
    text = " ".join(str(value) for value in state.values()).lower()
    for factor in ["probe", "fixture", "flowrate", "flow rate", "method", "site", "shift"]:
        if factor in text and factor not in factors:
            factors.append("pump flowrate" if factor in {"flowrate", "flow rate"} else factor)
    factor_text = ", ".join(dict.fromkeys(factors)) or "the extra factors"
    return (
        "Expanded is the right conversation when you need to study factors beyond "
        f"operator and part, such as {factor_text}. The standard app-compatible "
        "templates are Type 1, Crossed, and Nested; they keep headers fixed for the "
        "current uploaders. If those extra factors must be analyzed, plan an expanded "
        "study design first. If they will be held constant or documented outside the "
        "upload, I can generate the simpler crossed or nested template."
    )


def factor_definition_response() -> str:
    return (
        "In this app, a `factor` usually means an extra study condition you want "
        "to intentionally vary or track beyond the standard Gage R&R structure.\n\n"
        "For normal crossed or nested Gage R&R, `Part`, `Operator/Appraiser`, and "
        "`Trial` are the baseline structure. They are not usually what I would list "
        "first when you ask for additional factors. Type 1 is the exception: it uses "
        "one setup/operator and one reference part measured repeatedly.\n\n"
        "Good factor examples are things like probe/caliper identity, fixture, "
        "station, measurement method, location/site, shift, environment, batch, "
        "or pump flow rate. For example, if you compare Caliper 1 vs Caliper 2, "
        "the caliper identity is the factor being compared."
    )


def _is_factor_definition_question(prompt: str) -> bool:
    text = prompt.lower().strip()
    if "factor" not in text and "factors" not in text:
        return False
    definition_terms = [
        "what is", "what are", "define", "meaning", "mean", "example",
        "examples", "terminology", "nomenclature",
    ]
    return any(term in text for term in definition_terms) or len(text.split()) <= 8


def probe_comparison_response() -> str:
    return (
        "For Probe A vs Probe B, use a Crossed Gage R&R to compare the gage "
        "or instrument levels. In the template, use the `Operator` column for "
        "the probe identity when the actual human operator is held constant.\n\n"
        "Set up the data like this:\n"
        "- `Operator`: Probe A or Probe B\n"
        "- `Part`: the part/sample being measured\n"
        "- `Trial`: the repeat number\n"
        "- `Value`: the measured reading\n\n"
        "Measure the same parts with both probes, and repeat each part/probe "
        "combination for the planned number of trials. Keep the person, method, "
        "fixture, station, and environment as constant as practical.\n\n"
        "The probe/instrument is the factor you are comparing, but it is not "
        "the only source of variation. The parts and repeated trials are still "
        "needed so the study "
        "can separate probe-to-probe difference from part-to-part variation and "
        "normal repeatability noise."
    )


def _history_mentions_probe(history: list[dict[str, Any]] | None) -> bool:
    if not history:
        return False
    recent = " ".join(
        message.get("content", "")
        for message in history[-6:]
        if isinstance(message, dict)
    ).lower()
    return "probe" in recent


def _is_probe_comparison_question(
    prompt: str,
    history: list[dict[str, Any]] | None = None,
) -> bool:
    text = prompt.lower()
    mentions_probe = "probe" in text or _history_mentions_probe(history)
    if not mentions_probe:
        return False
    probe_level_comparison = bool(
        re.search(r"\bprobe\s+a\b", text)
        and re.search(r"\bprobe\s+b\b", text)
    )
    comparison_terms = [
        "difference", "compare", "comparison", "just probe", "only probe",
        "probe is the only", "only factor", "one factor", "treat the probe",
        "treat probe",
    ]
    crossed_terms = ["crossed", "appraiser", "operator", "replicate", "trial"]
    return probe_level_comparison or any(term in text for term in comparison_terms) or (
        "crossed" in text and any(term in text for term in crossed_terms)
    )


def _detect_measurement_design(prompt: str) -> dict[str, Any]:
    text = prompt.lower()
    design: dict[str, Any] = {}
    if (
        "non-destructive" in text
        or "nondestructive" in text
        or "non destructive" in text
        or "reusable" in text
        or "reuse the samples" in text
        or "reuse the parts" in text
        or "same samples" in text
        or "same parts" in text
    ):
        design["destructive_status"] = "non-destructive"
        design["reusable_parts"] = True
    elif "destructive" in text or "destroyed" in text or "cannot reuse" in text:
        design["destructive_status"] = "destructive"
    if re.search(r"\b(\d+)\s+(?:operators?|appraisers?)\b", text):
        design["operators"] = int(re.search(r"\b(\d+)\s+(?:operators?|appraisers?)\b", text).group(1))
    elif "one operator" in text or "single operator" in text or "one appraiser" in text:
        design["operators"] = 1
    elif "operators" in text or "appraisers" in text:
        design["multiple_operators"] = True
    if re.search(r"\b(\d+)\s+(?:parts?|samples?|electrodes?|coupons?)\b", text):
        design["parts"] = int(re.search(r"\b(\d+)\s+(?:parts?|samples?|electrodes?|coupons?)\b", text).group(1))
    elif "one reference part" in text or "single reference part" in text:
        design["parts"] = 1
    trial_match = re.search(r"\b(\d+)\s+(?:trials?|repeats?|replicates?|repetitions?|times)\b", text)
    if trial_match:
        design["trials"] = int(trial_match.group(1))
    elif "repeated" in text:
        repeated_match = re.search(r"repeated\s+(\d+)", text)
        if repeated_match:
            design["trials"] = int(repeated_match.group(1))
    if any(word in text for word in ["probe", "pump", "flowrate", "flow rate", "fixture", "method", "site", "shift"]):
        design["extra_factors"] = True
    if "reference part" in text:
        design["reference_part"] = True
    return design


def _recommend_from_design(state: dict[str, Any]) -> tuple[str | None, str | None]:
    destructive_status = state.get("destructive_status")
    operators = state.get("operators")
    parts = state.get("parts")
    trials = state.get("trials")
    if operators == 1 and (parts == 1 or state.get("reference_part")) and trials:
        return "type1", "Recommendation: Type 1 Gage study. Use one setup or operator to repeatedly measure one reference part."
    if destructive_status == "destructive":
        if state.get("extra_factors"):
            return (
                "nested",
                "Recommendation: start with Nested as the simpler design because destructive testing prevents sharing the same parts across operators. Expanded is the more complete option if you also need to quantify probe, pump-flow, fixture, method, or other factor effects and can support the added runs and analysis.",
            )
        return "nested", "Recommendation: Nested Gage R&R. Use it because destructive testing prevents each operator from measuring the same physical parts."
    if destructive_status == "non-destructive" and (
        (operators and parts)
        or (state.get("multiple_operators") and state.get("reusable_parts"))
    ):
        return "crossed", "Recommendation: Crossed Gage R&R. With non-destructive testing, each operator can measure each part across the trials."
    return None, None


def _value_column_response(state: dict[str, Any]) -> str:
    return (
        "Use the measured response/readout as `Value`. For conductivity testing, "
        "`Value` should be the conductivity readout. Pump flowrate is a factor or "
        "setting, so hold it constant, document it, or include it as an expanded-study "
        "factor if you need to study its effect."
    )


def route_chat_turn(user_message: str, state: dict[str, Any] | None = None) -> RouterResult:
    current = dict(state or {})
    history = current.get("messages") or current.get("history") or []
    scope = classify_prompt_scope(user_message, history)
    if scope == "out_of_scope" and (
        current.get("selected_study_type") or current.get("pending_template_request")
    ):
        if _contains_any(user_message.lower(), FOLLOWUP_PATTERNS):
            scope = "direct"
    if scope == "out_of_scope":
        return RouterResult("redirect", out_of_scope_response(), current)
    if scope == "ambiguous":
        return RouterResult("ask_followup", ambiguous_scope_response(), current)

    previous_measurement = current.get("measurement_context")
    design = _detect_measurement_design(user_message)
    current.update(design)
    if design.get("multiple_operators") and "operators" not in design:
        current.pop("operators", None)
    measurement_context = detect_measurement_context(user_message)
    if measurement_context and previous_measurement and measurement_context != previous_measurement:
        for stale_key in ["operators", "parts", "trials", "reference_part"]:
            if stale_key not in design:
                current.pop(stale_key, None)
    if (
        design.get("destructive_status") == "non-destructive"
        and current.get("selected_study_type") == "nested"
        and "nested" not in user_message.lower()
    ):
        current["selected_study_type"] = "crossed"

    detected_study_type = detect_study_type(user_message)
    if detected_study_type:
        current["selected_study_type"] = detected_study_type

    if measurement_context:
        current["measurement_context"] = measurement_context

    template_type = detect_template_request(user_message)

    if template_type != "expanded" and re.search(r"\b(value|column|readout|what do i use|which do i use|flowrate|flow rate)\b", user_message, re.I) and (
        "value" in user_message.lower()
        or "readout" in user_message.lower()
        or "flowrate" in user_message.lower()
        or "flow rate" in user_message.lower()
    ):
        return RouterResult("call_model", _value_column_response(current), current)

    if template_type is None and _is_factor_definition_question(user_message):
        return RouterResult("call_model", factor_definition_response(), current)

    if (
        template_type is None
        and current.get("destructive_status") != "destructive"
        and _is_probe_comparison_question(user_message, history)
    ):
        current["extra_factors"] = True
        current["probe_comparison"] = True
        return RouterResult("call_model", probe_comparison_response(), current)

    recommended_type, recommendation = _recommend_from_design(current)
    if recommended_type:
        current["selected_study_type"] = recommended_type
        if (
            template_type is None
            and not current.get("pending_template_request")
            and "generate" not in user_message.lower()
            and "template" not in user_message.lower()
        ):
            return RouterResult("call_model", recommendation, current)

    if template_type is None and is_template_confirmation(user_message):
        template_type = current.get("selected_study_type") or "known"
    if template_type is None and current.get("selected_study_type") and any(
        phrase in user_message.lower()
        for phrase in ["make the file", "make file", "generate file", "download file", "create file"]
    ):
        template_type = current["selected_study_type"]

    pending_template = current.get("pending_template_request")
    if pending_template:
        template_type = (
            template_type
            or pending_template.get("study_type")
            or current.get("selected_study_type")
        )
        current["measurement_context"] = current.get("measurement_context") or pending_template.get("measurement_context")

    if template_type == "expanded":
        current["pending_template_request"] = None
        return RouterResult(
            "ask_followup",
            expanded_template_response(current),
            current,
            template_type="expanded",
            measurement_context=current.get("measurement_context"),
        )

    if (
        template_type == "crossed"
        and current.get("destructive_status") == "destructive"
    ):
        current["selected_study_type"] = "nested"
        current["pending_template_request"] = {
            "study_type": "nested",
            "measurement_context": current.get("measurement_context"),
        }
        return RouterResult(
            "ask_followup",
            (
                "Crossed is not appropriate if the measurement is destructive, "
                "because each operator cannot measure the same physical parts. "
                "Use a Nested Gage R&R template instead. Should I generate the "
                "nested template?"
            ),
            current,
            template_type="nested",
            measurement_context=current.get("measurement_context"),
        )

    missing_study_type = template_type == "known" and not current.get("selected_study_type")
    if template_type == "known":
        template_type = current.get("selected_study_type")

    if missing_study_type:
        current["pending_template_request"] = {
            "study_type": None,
            "measurement_context": current.get("measurement_context"),
        }
        return RouterResult(
            "ask_followup",
            template_followup_question(None, ["study_type"]),
            current,
            measurement_context=current.get("measurement_context"),
        )

    if template_type:
        missing = []
        if not template_type:
            missing.append("study_type")
        if template_type == "crossed" and current.get("destructive_status") != "non-destructive":
            missing.append("destructive_status")
        measurement_context = current.get("measurement_context")
        if template_type == "type1" and not measurement_context:
            missing.append("measurement_context")
        if missing:
            current["pending_template_request"] = {
                "study_type": template_type,
                "measurement_context": measurement_context,
            }
            return RouterResult(
                "ask_followup",
                template_followup_question(template_type, missing),
                current,
                template_type=template_type,
                measurement_context=measurement_context,
            )
        current["pending_template_request"] = None
        message = template_chat_response(template_type, measurement_context)
        return RouterResult(
            "generate_template",
            message,
            current,
            template_type=template_type,
            measurement_context=measurement_context,
        )

    return RouterResult("call_model", "", current)
