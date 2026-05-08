from gage_rr_companion.doe_workflow import guided_step_states, recommend_guided_study, template_help


def test_initial_guided_flow_only_q1_active():
    states = guided_step_states({})

    assert states["q1"] == "active"
    assert states["q2"] == "locked"
    assert states["template"] == "locked"


def test_repeatability_only_unlocks_type1_template():
    answers = {"scope": "repeatability_only"}

    states = guided_step_states(answers)
    recommendation = recommend_guided_study(answers)

    assert states["recommendation"] == "complete"
    assert states["template"] == "active"
    assert recommendation.study_type == "type1"


def test_rr_path_unlocks_questions_in_order():
    states = guided_step_states({"scope": "repeatability_reproducibility"})

    assert states["q1"] == "complete"
    assert states["q2"] == "active"
    assert states["q3"] == "locked"

    states = guided_step_states(
        {"scope": "repeatability_reproducibility", "multiple_parameters": False}
    )

    assert states["q2"] == "complete"
    assert states["q3"] == "active"
    assert states["template"] == "locked"


def test_multiple_parameters_recommends_expanded_but_still_asks_q3():
    result = recommend_guided_study(
        {"scope": "repeatability_reproducibility", "multiple_parameters": True}
    )
    states = guided_step_states(
        {"scope": "repeatability_reproducibility", "multiple_parameters": True}
    )

    assert result.study_type == "expanded"
    assert states["q3"] == "active"
    assert "focus" in result.caution.lower()


def test_destructive_recommends_nested_for_one_parameter():
    recommendation = recommend_guided_study(
        {
            "scope": "repeatability_reproducibility",
            "multiple_parameters": False,
            "destructive": True,
        }
    )

    assert recommendation.study_type == "nested"
    assert "destructive" in recommendation.reason


def test_non_destructive_recommends_crossed_for_one_parameter():
    recommendation = recommend_guided_study(
        {
            "scope": "repeatability_reproducibility",
            "multiple_parameters": False,
            "destructive": False,
        }
    )

    assert recommendation.study_type == "crossed"
    assert "not destructive" in recommendation.reason


def test_template_help_describes_expanded_use_case():
    assert "more than one" in template_help("expanded")
