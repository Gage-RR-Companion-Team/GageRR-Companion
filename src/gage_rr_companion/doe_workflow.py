from __future__ import annotations

from dataclasses import dataclass


GUIDED_STEP_IDS = ("q1", "q2", "q3", "recommendation", "template")

STUDY_LABELS = {
    "type1": "Type 1 Gage Study",
    "crossed": "Crossed Gage R&R",
    "nested": "Nested Gage R&R",
    "expanded": "Expanded Gage R&R",
}

STUDY_PLAIN_LABELS = {
    "type1": "Repeatability only",
    "crossed": "Repeatability and reproducibility, non-destructive",
    "nested": "Repeatability and reproducibility, destructive",
    "expanded": "More than one measurable parameter",
}

TEMPLATE_COMPATIBILITY = {
    "type1": "Use this when you only need repeatability for one measurement process.",
    "crossed": "Use this when every person can measure the same parts and the test is not destructive.",
    "nested": "Use this when testing changes, damages, consumes, or otherwise prevents reusing the same part.",
    "expanded": "Use this when you need to assess more than one measurable parameter or source of measurement variation.",
}


@dataclass(frozen=True)
class DoeRecommendation:
    study_type: str | None
    label: str | None
    reason: str
    next_step: str
    caution: str | None = None


def guided_step_states(answers: dict[str, str | bool | None]) -> dict[str, str]:
    """Return UI state for each guided flowchart step."""

    states = {step_id: "locked" for step_id in GUIDED_STEP_IDS}
    states["q1"] = "active"

    scope = answers.get("scope")
    multiple_parameters = answers.get("multiple_parameters")
    destructive = answers.get("destructive")

    if scope:
        states["q1"] = "complete"
        if scope == "repeatability_only":
            states["recommendation"] = "complete"
            states["template"] = "active"
            return states
        states["q2"] = "active"

    if scope == "repeatability_reproducibility" and multiple_parameters is not None:
        states["q2"] = "complete"
        states["q3"] = "active"
        if multiple_parameters:
            states["recommendation"] = "complete"

    if (
        scope == "repeatability_reproducibility"
        and multiple_parameters is not None
        and destructive is not None
    ):
        states["q3"] = "complete"
        states["recommendation"] = "complete"
        states["template"] = "active"

    return states


def recommend_guided_study(answers: dict[str, str | bool | None]) -> DoeRecommendation:
    """Recommend a study type from the guided DOE answers."""

    scope = answers.get("scope")
    multiple_parameters = answers.get("multiple_parameters")
    destructive = answers.get("destructive")

    if not scope:
        return DoeRecommendation(
            study_type=None,
            label=None,
            reason="Start by choosing whether you need repeatability only, or repeatability and reproducibility.",
            next_step="Answer Q1 to begin the flow.",
        )

    if scope == "repeatability_only":
        return DoeRecommendation(
            study_type="type1",
            label=STUDY_LABELS["type1"],
            reason="You only need to identify repeatability, so a Type 1 study is the best fit.",
            next_step="Generate the Type 1 template and collect repeated readings for one measurement process.",
        )

    if multiple_parameters is None:
        return DoeRecommendation(
            study_type=None,
            label=None,
            reason="Next, decide whether the study needs one measurable parameter or more than one.",
            next_step="Answer Q2 to continue the flow.",
        )

    if multiple_parameters and destructive is None:
        return DoeRecommendation(
            study_type="expanded",
            label=STUDY_LABELS["expanded"],
            reason="More than one measurable parameter points toward an Expanded Gage R&R.",
            next_step="Still answer Q3 so Cornelius can help choose the cleanest starting template.",
            caution="Friendly suggestion: focus the first test on one aspect of the measurement system if you can. It keeps the study easier to run and the results easier to explain.",
        )

    if destructive is None:
        return DoeRecommendation(
            study_type=None,
            label=None,
            reason="One measurable parameter is enough for a standard Gage R&R. Now choose whether the test is destructive.",
            next_step="Answer Q3 to choose nested or crossed.",
        )

    if multiple_parameters:
        return DoeRecommendation(
            study_type="expanded",
            label=STUDY_LABELS["expanded"],
            reason=(
                "More than one measurable parameter points toward an Expanded Gage R&R. "
                f"Because the test is {'destructive' if destructive else 'not destructive'}, use that detail when narrowing the first run plan."
            ),
            next_step="Ask Cornelius which single aspect to focus on first, or simplify to a nested/crossed study for the first template.",
            caution="Friendly suggestion: focus the first test on one aspect of the measurement system if you can. It keeps the study easier to run and the results easier to explain.",
        )

    if destructive:
        return DoeRecommendation(
            study_type="nested",
            label=STUDY_LABELS["nested"],
            reason="The testing is destructive, so parts cannot be reused across people. Nested Gage R&R is the best fit.",
            next_step="Generate the nested template, collect the readings, then upload the completed file on the analysis page.",
        )

    return DoeRecommendation(
        study_type="crossed",
        label=STUDY_LABELS["crossed"],
        reason="The testing is not destructive, so each person can measure the same parts. Crossed Gage R&R is the best fit.",
        next_step="Generate the crossed template, collect the readings, then upload the completed file on the analysis page.",
    )


def template_help(study_type: str) -> str:
    return TEMPLATE_COMPATIBILITY[study_type]
