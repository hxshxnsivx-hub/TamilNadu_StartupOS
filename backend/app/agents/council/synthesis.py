"""What the founder hears from the council: a few sentences and one question.

Built by code from the vote and the cited claims only, so it cannot introduce
a fact the seats did not back; each sentence still passes the fact check
against the evidence pack. The founder hears one synthesis, never seven voices.
"""

from __future__ import annotations

from app.agents.council.evidence import EvidencePack
from app.agents.council.seats import BY_ID, CRITERION_WORDS, Opinion
from app.agents.grounding import facts_from, gate

BAND_LINE = {
    "strong": "Looking at it from seven angles, the idea holds up well so far.",
    "mixed": "Looking at it from seven angles, the picture is mixed.",
    "weak": "Looking at it from seven angles, there are serious concerns to work through.",
}


def _clause(text: str) -> str:
    """A claim placed after a colon: lower-case start (unless an acronym), no full stop."""
    t = text.strip().rstrip(".")
    return t if t[:2].isupper() else t[:1].lower() + t[1:]


def synthesise(vote: dict, opinions: list[Opinion], pack: EvidencePack) -> dict:
    by_seat = {o.seat: o for o in opinions}
    lines = [BAND_LINE[vote["band"]]]

    if vote["blockers"]:
        b = vote["blockers"][0]
        lines.append(f"The biggest concern, from the {BY_ID[b['seat']].name.lower()} view:"
                     f" {_clause(b['text'])}.")  # fmt: skip

    crit = vote["criteria"]
    if crit:
        best = max(crit, key=lambda c: crit[c]["score"])
        seat = by_seat.get(crit[best]["high"])
        if crit[best]["score"] >= 3.5 and seat and seat.claims:
            lines.append(f"On {CRITERION_WORDS[best]}, it looks good: "
                         f"{_clause(seat.claims[0].text)}.")  # fmt: skip
        worst = min(crit, key=lambda c: crit[c]["score"])
        seat = by_seat.get(crit[worst]["low"])
        if worst != best and crit[worst]["score"] < 3 and seat and seat.claims:
            lines.append(f"The weakest point is {CRITERION_WORDS[worst]}: "
                         f"{_clause(seat.claims[0].text)}.")  # fmt: skip

    if vote["ask_about"]:
        lines.append(f"The views differ most on {CRITERION_WORDS[vote['ask_about']]}.")

    alts = [v for v in vote["variants"] if not v.get("as_described")]
    if alts:
        lines.append(f"One option the panel suggests: {_clause(alts[0]['text'])}.")

    facts = facts_from(pack.lines())
    said = [s for s in (gate(line, facts) for line in lines) if s]
    return {
        "voice_brief": said,
        "dropped": len(lines) - len(said),
        "question": vote["question"],
        "variants": vote["variants"],
    }
