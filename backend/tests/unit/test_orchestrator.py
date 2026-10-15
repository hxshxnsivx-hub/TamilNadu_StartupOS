"""Unit tests for intent classification and the orchestrator routing/context."""

import pytest
from app.orchestrator.intent import Intent, classify_keywords
from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import ConversationState


@pytest.mark.parametrize(
    "text,intent,swarm",
    [
        ("I have a startup idea about solar pumps", Intent.IDEA_INPUT, "roadmap"),
        ("which government scheme am I eligible for?", Intent.SCHEME_QUERY, "scheme"),
        ("find me a supplier for raw material", Intent.B2B_SEARCH, "b2b"),
        ("am I ready to raise funding from an investor?", Intent.FUNDING_QUERY, "funding"),
        ("I want to upload my Aadhaar document", Intent.DOCUMENT_UPLOAD, "profile"),
        ("show me the roadmap and next steps", Intent.ROADMAP_REQUEST, "roadmap"),
        ("update my profile, my name is Selvi", Intent.PROFILE_UPDATE, "profile"),
    ],
)
def test_keyword_classification(text, intent, swarm):
    c = classify_keywords(text)
    assert c.intent == intent
    assert c.swarm == swarm
    assert c.confidence >= 0.8  # single strong keyword auto-routes


def test_general_question_routes_to_orchestrator():
    c = classify_keywords("hello, what is this platform?")
    assert c.intent == Intent.GENERAL_QUESTION
    assert c.swarm == "orchestrator"
    assert not c.should_clarify


def test_orchestrator_routes_and_records_message():
    orch = Orchestrator()
    st = ConversationState(user_id="u1", session_id="s1")
    d = orch.handle_turn(st, "which scheme am I eligible for?")
    assert d.action == "route"
    assert d.swarm == "scheme"
    assert st.active_swarm == "scheme"
    assert st.messages[-1].content.startswith("which scheme")


def test_context_switch_pushes_and_resumes():
    orch = Orchestrator()
    st = ConversationState(user_id="u1", session_id="s1")

    orch.handle_turn(st, "help me build a roadmap")  # active = roadmap
    assert st.active_swarm == "roadmap"

    orch.handle_turn(st, "wait, which scheme am I eligible for?")  # switch → scheme
    assert st.active_swarm == "scheme"
    assert len(st.context_stack) == 1  # roadmap task remembered

    resumed = orch.resume(st)  # return to roadmap
    assert resumed["swarm"] == "roadmap"
    assert st.active_swarm == "roadmap"
    assert st.context_stack == []
