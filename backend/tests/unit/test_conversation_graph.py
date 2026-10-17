"""Unit tests for the conversation state machine: nodes, intent edges, context stack."""

import pytest
from app.orchestrator import handlers
from app.orchestrator.graph import ConversationGraph, HandlerResult
from app.orchestrator.intent import Classification, Intent, classify_keywords
from app.orchestrator.state import ConversationState


class Fakes:
    """Task handlers that record what reached them; `done` says which finish in one turn."""

    def __init__(self, done=("scheme_discovery", "profile_collection"), fail=()):
        self.calls: list[tuple[str, str]] = []
        self.done = set(done)
        self.fail = set(fail)

    def table(self):
        def make(node):
            async def handle(ctx):
                self.calls.append((node, ctx.text))
                if node in self.fail:
                    raise RuntimeError("swarm down")
                return HandlerResult(f"{node} reply to {ctx.text!r}", node in self.done)

            return handle

        return {n: make(n) for n in ConversationGraph.TASK_NODES}


def _state() -> ConversationState:
    return ConversationState(user_id="u1", session_id="s1")


async def test_pure_greeting_is_answered_by_the_greeting_node():
    f = Fakes()
    st = _state()
    r = await ConversationGraph(f.table()).step(st, "Vanakkam!")
    assert r.node == "greeting" and r.action == "greet"
    assert f.calls == [] and st.active_swarm is None
    assert [t.role for t in st.messages] == ["user", "assistant"]


@pytest.mark.parametrize(
    "text,node,swarm",
    [
        ("I have a startup idea about solar pumps", "idea_discussion", "roadmap"),
        ("show me the roadmap and next steps", "idea_discussion", "roadmap"),
        ("which government scheme am I eligible for?", "scheme_discovery", "scheme"),
        ("update my profile, my name is Selvi", "profile_collection", "profile"),
        ("I want to upload my Aadhaar document", "profile_collection", "profile"),
        ("find me a supplier for raw material", "b2b_matching", "b2b"),
        ("am I ready to raise funding from an investor?", "funding_assessment", "funding"),
    ],
)
async def test_intent_edges_dispatch_to_the_owning_node(text, node, swarm):
    f = Fakes(done=())
    st = _state()
    r = await ConversationGraph(f.table()).step(st, text)
    assert f.calls == [(node, text)]
    assert (r.node, r.swarm, r.action) == (node, swarm, "route")
    assert st.active_swarm == swarm and st.node == node


async def test_no_signal_and_no_task_asks_a_clarifying_question():
    f = Fakes()
    st = _state()
    r = await ConversationGraph(f.table()).step(st, "what is the weather like")
    assert r.node == "clarification" and r.action == "clarify"
    assert f.calls == [] and st.active_swarm is None
    assert "scheme" in r.reply.lower()


async def test_low_confidence_classification_clarifies_instead_of_guessing():
    def unsure(text):
        return Classification(Intent.SCHEME_QUERY, 0.6, "scheme", ("eligible",))

    f = Fakes()
    r = await ConversationGraph(f.table(), classifier=unsure).step(_state(), "eligible?")
    assert r.node == "clarification" and f.calls == []


async def test_follow_up_without_a_signal_continues_the_active_task():
    f = Fakes(done=())
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    r = await g.step(st, "Chennai")
    assert f.calls[-1] == ("idea_discussion", "Chennai")
    assert r.action == "continue" and r.node == "idea_discussion"
    assert st.context_stack == []


FUNDING_Q = "How do you expect to fund it — your own money, a loan, a grant, investors?"
TEAM_Q = "How many people will be working on this?"


@pytest.mark.parametrize(
    "question,answer",
    [
        (FUNDING_Q, "a grant"),
        (FUNDING_Q, "investors"),
        (FUNDING_Q, "a grant?"),
        (TEAM_Q, "me and a partner"),
        (TEAM_Q, "government subsidy covers part"),
        (TEAM_Q, "we buy raw material locally"),
        (TEAM_Q, "a platform connecting farmers to vendors"),
        (TEAM_Q, "yes, I have a pitch deck idea"),
    ],
)
async def test_an_answer_to_the_tasks_own_question_is_not_a_switch(question, answer):
    f = Fakes(done=())
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    st.last_question = question  # what the idea agent asked last
    r = await g.step(st, answer)
    assert f.calls[-1] == ("idea_discussion", answer)
    assert (r.action, r.node) == ("continue", "idea_discussion")
    assert st.context_stack == [] and st.active_swarm == "roadmap"


@pytest.mark.parametrize(
    "text",
    [
        "wait, which scheme am I eligible for?",
        "am I eligible for any scheme",
        "find me a supplier",
        "can I raise funding from an investor",
        "show me my profile",
    ],
)
async def test_a_clear_request_still_switches_mid_task(text):
    f = Fakes(done=())
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    st.last_question = TEAM_Q
    r = await g.step(st, text)
    assert r.action == "route" and r.swarm != "roadmap"
    assert [c["swarm"] for c in st.context_stack] == ["roadmap"]


async def test_switch_pauses_the_task_and_a_finished_detour_resumes_it():
    f = Fakes()
    g = ConversationGraph(f.table())
    st = _state()
    first = await g.step(st, "I have a startup idea: a nurse alert device")

    r = await g.step(st, "wait, which scheme am I eligible for?")
    assert f.calls[-1][0] == "scheme_discovery"
    assert r.swarm == "scheme" and r.paused == []  # detour done, nothing left paused
    assert r.resumed["swarm"] == "roadmap"
    assert st.active_swarm == "roadmap" and st.node == "idea_discussion"
    assert first.reply in r.reply  # the idea's open question is asked again

    await g.step(st, "Chennai")  # back in the idea, so this answers its question
    assert f.calls[-1] == ("idea_discussion", "Chennai")


async def test_switch_to_an_ongoing_task_keeps_the_first_paused_until_asked_back():
    f = Fakes(done=())
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    r = await g.step(st, "find me a supplier for raw material")
    assert r.paused == ["roadmap"] and st.active_swarm == "b2b"

    r = await g.step(st, "ok, let's go back")
    assert r.action == "resume" and r.node == "idea_discussion"
    assert st.active_swarm == "roadmap" and st.context_stack == []
    assert len(f.calls) == 2  # resuming repeats the question; it calls no handler


async def test_go_back_with_nothing_paused_is_not_a_resume():
    r = await ConversationGraph(Fakes().table()).step(_state(), "go back")
    assert r.action == "clarify"


async def test_returning_to_a_paused_swarm_by_intent_drops_its_stale_entry():
    f = Fakes(done=())
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    await g.step(st, "find me a supplier for raw material")
    await g.step(st, "show me the roadmap")
    assert st.active_swarm == "roadmap"
    assert [c["swarm"] for c in st.context_stack] == ["b2b"]


async def test_a_failing_handler_goes_to_error_handling_and_leaves_state_as_it_was():
    f = Fakes(done=(), fail=("scheme_discovery",))
    g = ConversationGraph(f.table())
    st = _state()
    await g.step(st, "I have a startup idea: a nurse alert device")
    r = await g.step(st, "which scheme am I eligible for?")
    assert r.node == "error_handling" and r.action == "error"
    assert st.active_swarm == "roadmap" and st.node == "idea_discussion"
    assert st.context_stack == []
    assert st.messages[-1].role == "assistant"


def test_state_survives_a_save_and_load():
    st = _state()
    st.add_message("user", "hi")
    st.active_swarm, st.node, st.last_question = "b2b", "b2b_matching", "Which product?"
    st.push_context()
    back = ConversationState.from_dict(st.to_dict())
    assert back == st
    back.active_swarm = "scheme"
    assert back.pop_context()["node"] == "b2b_matching"
    assert back.last_question == "Which product?"


# --- the default handlers (offline, deterministic) ---------------------------


def _ctx(text, state=None, session=None):
    st = state or _state()
    return handlers.TurnContext(st, session, text, classify_keywords(text), None)


async def test_profile_handler_records_the_name_and_reports_completeness():
    st = _state()
    r = await handlers.profile_collection(_ctx("update my profile, my name is Selvi", st))
    assert st.entities["profile"]["founder"]["name"] == "Selvi"
    assert r.done and r.data["score"] == 0 and "founder.email" in r.data["missing_fields"]


async def test_scheme_handler_checks_every_seeded_scheme():
    r = await handlers.scheme_discovery(_ctx("which scheme am I eligible for?"))
    assert r.done and r.data["total_checked"] > 0
    assert len(r.data["eligible"]) <= 3


async def test_funding_handler_scores_readiness_with_a_next_step():
    r = await handlers.funding_assessment(_ctx("am I ready to raise funding?"))
    assert r.done and r.data["band"] == "Not Ready" and r.data["next_step"]


async def test_b2b_handler_drafts_a_bill_of_materials():
    r = await handlers.b2b_matching(_ctx("find a supplier for my product"))
    assert r.done and r.data["bom"]


async def test_roadmap_request_without_an_idea_asks_for_it():
    from app.agents import ideation

    s, _ = ideation.new_session("Kavya")
    r = await handlers.idea_discussion(_ctx("show me the roadmap", session=s))
    assert not r.done and "idea" in r.reply.lower() and r.data["roadmap"] is None


async def test_roadmap_request_with_an_idea_returns_the_roadmap():
    from app.agents import ideation

    s, _ = ideation.new_session("Kavya")
    s.idea = "An affordable agri IoT device to help farmers with irrigation."
    r = await handlers.idea_discussion(_ctx("show me the roadmap", session=s))
    assert r.data["roadmap"]["milestones"] and "milestones" in r.reply
