"""The quality test set: ten founder ideas, each a full offline conversation.

Fails with the list of broken expectations for that idea. Research is
replayed from fixtures/, so this runs without network or keys; refresh the
fixtures with scripts/record_eval_fixtures.py. The readable report is
scripts/eval_report.py -> docs/eval/report.md.
"""

from __future__ import annotations

import pytest

from tests.eval.runner import EVAL, load_ideas, run_idea

IDEAS = load_ideas()


def test_every_idea_has_a_recording():
    missing = [i["id"] for i in IDEAS if not (EVAL / "fixtures" / f"{i['id']}.json").exists()]
    assert not missing, f"record them with scripts/record_eval_fixtures.py: {missing}"


@pytest.mark.parametrize("idea", IDEAS, ids=[i["id"] for i in IDEAS])
async def test_idea(idea):
    result = await run_idea(idea)
    problems = [f"{c.name}: {c.detail}" for c in result.failures()]
    assert not problems, "\n".join(problems)
