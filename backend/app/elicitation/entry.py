"""What the front door's two answers mean to the conversation and the journey
(tasks 1.1.5.1, 1.1.6; R121).

The Start screen asks two things and the browser keeps them (frontend
journeyStore.ts):

  entry mode   idea | domain_only | intent_only      (app.models.enums.EntryMode)
  reg subtype  registered_with_product (2A) | registered_no_product (2B)
               | idea_worker_no_company (2C) | unregistered
                                                      (app.models.enums.RegSubtype)

Both arrive typed at session start (routers/ideation.py AgentStartIn), and the
journey takes the subtype too (routers/journey.py). This is the one place that
says what they mean, so the agent, the greeting and the journey engine cannot
each invent a reading:

  * a subtype says whether the startup is registered, its legal structure when
    that follows (nothing registered means no structure), the lowest stage it
    can be at, and how the conversation opens;
  * an entry mode says which conversation runs (EntryMode in slots.py). A
    domain_only founder's domain is the profile's sector, sent with it.

The stage floor is a reading of the Start screen's own words ("it sells or
ships something" is at least a first version, MVP); only that subtype implies a
stage. The floor is said back as an assumption, never stored as the founder's
answer, so a wrong reading costs one correction at the restatement.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.stages import Stage
from app.elicitation.slots import EntryMode
from app.models.enums import EntryMode as Door
from app.models.enums import RegSubtype


@dataclass(frozen=True)
class Registration:
    registered: bool
    # the journey's entity value when the subtype settles it; None leaves it asked
    entity: str | None
    stage_floor: Stage | None
    # the first question, and the sentence before it in the greeting
    opening: str
    lead: str
    # how the model hears it, among the facts known so far
    said: str


REGISTRATION: dict[RegSubtype, Registration] = {
    RegSubtype.REGISTERED_WITH_PRODUCT: Registration(
        registered=True,
        entity=None,
        stage_floor=Stage.MVP,
        opening="Tell me about the product your company sells, and who buys it.",
        lead="Your company is registered and already has a product, so we start from the"
        " product, not from an idea.",
        said="a registered company with a product it sells or ships",
    ),
    RegSubtype.REGISTERED_NO_PRODUCT: Registration(
        registered=True,
        entity=None,
        stage_floor=None,
        opening="Tell me about the product your company is building, in your own words.",
        lead="Your company is registered and nothing has shipped yet.",
        said="a registered company with no product yet",
    ),
    RegSubtype.IDEA_WORKER_NO_COMPANY: Registration(
        registered=False,
        entity="none",
        stage_floor=None,
        opening="Tell me about what you are building or researching, in your own words.",
        lead="You are already working on it, without a company yet.",
        said="working on it, no company registered",
    ),
    RegSubtype.UNREGISTERED: Registration(
        registered=False,
        entity="none",
        stage_floor=None,
        opening="Tell me about the idea you are working on, in your own words.",
        lead="",
        said="nothing registered yet",
    ),
}

# Which conversation each entry mode runs. The experience conversation's own
# questions, ranking and research gate are task 1.1.5 (R089, R048, R118); until
# 1.1.5.2 switches this on, every session runs the idea conversation and keeps
# the entry mode for it.
CONVERSATION_MODE: dict[Door, EntryMode] = {
    Door.IDEA: EntryMode.IDEA,
    Door.DOMAIN_ONLY: EntryMode.EXPERIENCE,
    Door.INTENT_ONLY: EntryMode.EXPERIENCE,
}


def journey_facts(subtype: RegSubtype | str | None) -> dict:
    """The journey facts a subtype settles (registered, and entity when it follows);
    a fact the founder states outranks them."""
    if subtype is None:
        return {}
    r = REGISTRATION[RegSubtype(subtype)]
    facts: dict = {"registered": r.registered}
    if r.entity is not None:
        facts["entity"] = r.entity
    return facts
