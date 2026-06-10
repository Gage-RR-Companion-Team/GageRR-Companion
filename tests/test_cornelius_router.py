from gage_rr_companion.cornelius_router import route_chat_turn


def test_template_request_without_study_type_asks_followup():
    result = route_chat_turn("Generate an Excel template for my study", {})

    assert result.action == "ask_followup"
    assert "study type" in result.message.lower()
    assert result.template_type is None


def test_crossed_context_is_captured_then_confirmation_generates_template():
    state = {}

    first = route_chat_turn(
        "I have a non-destructive study with 2 operators, 24 electrodes, and 3 trials.",
        state,
    )

    assert first.action == "call_model"
    assert first.updated_state["selected_study_type"] == "crossed"
    assert first.updated_state["destructive_status"] == "non-destructive"
    assert "Crossed" in first.message

    second = route_chat_turn("yes generate template", first.updated_state)

    assert second.action == "generate_template"
    assert second.template_type == "crossed"
    assert "Test #, Operator, Part, Trial, Value" in second.message


def test_crossed_template_request_waits_for_non_destructive_confirmation():
    result = route_chat_turn("Generate a crossed template for conductivity", {})

    assert result.action == "ask_followup"
    assert "destructive" in result.message.lower()


def test_pending_template_resumes_when_user_supplies_study_type():
    first = route_chat_turn("Generate an Excel template for my study", {})
    second = route_chat_turn("crossed", first.updated_state)

    assert second.action == "ask_followup"
    assert second.template_type == "crossed"
    assert "destructive" in second.message.lower()


def test_destructive_extra_factors_mentions_nested_and_expanded():
    result = route_chat_turn(
        "This is destructive membrane testing with probe and pump-flow variability.",
        {},
    )

    assert result.action == "call_model"
    assert "Nested" in result.message
    assert "Expanded" in result.message
    assert "simpler" in result.message
    assert "complete" in result.message


def test_value_column_guidance_for_conductivity_and_flowrate():
    result = route_chat_turn(
        "What value do I use, pump flowrate or conductivity readout?",
        {},
    )

    assert result.action == "call_model"
    assert "conductivity readout" in result.message
    assert "factor" in result.message


def test_unrelated_prompt_redirects_to_msa():
    result = route_chat_turn("Write me a recipe for dinner", {})

    assert result.action == "redirect"
    assert "Gage R&R" in result.message


def test_crossed_template_destructive_conflict_recommends_nested():
    result = route_chat_turn("I need a crossed template, it is destructive", {})

    assert result.action == "ask_followup"
    assert result.template_type == "nested"
    assert result.updated_state["selected_study_type"] == "nested"
    assert "crossed" in result.message.lower()
    assert "destructive" in result.message.lower()
    assert "nested" in result.message.lower()


def test_non_destructive_repeats_template_infers_crossed():
    result = route_chat_turn(
        "non destructive 2 appraisers 10 parts 3 repeats make template",
        {},
    )

    assert result.action == "generate_template"
    assert result.template_type == "crossed"
    assert result.updated_state["trials"] == 3


def test_type1_template_inferred_from_reference_part():
    result = route_chat_turn(
        "I have one operator one reference part repeated 30 times, template for conductivity",
        {},
    )

    assert result.action == "generate_template"
    assert result.template_type == "type1"
    assert result.measurement_context == "conductivity"


def test_expanded_template_request_explains_standard_template_limit():
    result = route_chat_turn("expanded template for probe fixture flowrate", {})

    assert result.action == "ask_followup"
    assert "expanded" in result.message.lower()
    assert "standard" in result.message.lower()
    assert "probe" in result.message.lower()


def test_new_reusable_context_overrides_stale_destructive_state():
    stale_state = {
        "destructive_status": "destructive",
        "selected_study_type": "nested",
        "extra_factors": True,
    }

    result = route_chat_turn(
        "I want a template for membrane conductivity, parts are reusable but operators use different probes",
        stale_state,
    )

    assert result.updated_state["destructive_status"] == "non-destructive"
    assert result.updated_state["selected_study_type"] == "crossed"
    assert result.template_type == "crossed"


def test_reusable_parts_with_operators_infers_crossed_template():
    result = route_chat_turn(
        "I want a template for membrane conductivity, parts are reusable but operators use different probes",
        {},
    )

    assert result.action == "generate_template"
    assert result.template_type == "crossed"
    assert result.updated_state["extra_factors"] is True


def test_make_file_after_recommendation_generates_selected_template():
    first = route_chat_turn(
        "I have a non-destructive study with 2 operators, 24 electrodes, and 3 trials.",
        {},
    )
    second = route_chat_turn("make the file", first.updated_state)

    assert second.action == "generate_template"
    assert second.template_type == "crossed"


def test_probe_a_vs_probe_b_recommends_crossed_without_expanded():
    result = route_chat_turn("Probe A vs Probe B", {})

    assert result.action == "call_model"
    assert "Crossed Gage R&R" in result.message
    assert "instrument" in result.message
    assert "Expanded" not in result.message


def test_probe_only_comparison_recommends_crossed_without_expanded():
    result = route_chat_turn(
        "I'd like to see the difference with just Probe A and Probe B",
        {},
    )

    assert result.action == "call_model"
    assert "Crossed Gage R&R" in result.message
    assert "Probe A" in result.message
    assert "Probe B" in result.message
    assert "instrument" in result.message
    assert "Expanded" not in result.message


def test_probe_is_compared_factor_not_only_variation_source():
    first = route_chat_turn(
        "I'd like to see the difference with just Probe A and Probe B",
        {},
    )
    result = route_chat_turn(
        "But would it be correct to assume the probe is the only factor",
        first.updated_state,
    )

    assert "not the only source of variation" in result.message
    assert "part-to-part variation" in result.message
    assert "repeatability" in result.message
    assert "Expanded" not in result.message


def test_probe_guidance_does_not_call_operator_the_main_factor():
    result = route_chat_turn("What is the factor if I compare Probe A vs Probe B?", {})

    assert "caliper identity is the factor being compared" in result.message
    assert "baseline structure" in result.message
    assert "main comparison factor" not in result.message


def test_factor_definition_defaults_to_non_standard_study_conditions():
    result = route_chat_turn("What is a factor?", {})

    assert result.action == "call_model"
    assert "baseline structure" in result.message
    assert "probe/caliper identity" in result.message
    assert "fixture" in result.message
    assert "Operator: The person" not in result.message
    assert "Part: The specific item" not in result.message
