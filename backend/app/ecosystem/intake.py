"""Is an incubator taking applications? Read from the words on its own pages.

scripts/check_incubator_intake.py fetches each incubator's site weekly and hands
the visible text to classify_intake(); the result is stored in
data/incubator_intake.json and read by the matcher.

Status, in order of precedence:
  open        a deadline today or later, or open-call wording ("applications open",
              "call for startups") with no past-only deadline
  closed      closed wording ("applications closed"), or only deadlines that have passed
  rolling     only a standing "apply now" button: applications taken any time, no call
  apply_page  an application page exists but names no dates or status
  unknown     nothing about intake found
A check older than STALE_DAYS is not used: intake changes faster than that.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "incubator_intake.json"
STALE_DAYS = 14

OPEN = re.compile(
    r"applications? (?:are )?(?:now )?open|now accepting|accepting applications|"
    r"applications? invited|inviting applications|call for (?:applications|startups|proposals)|"
    r"registrations? (?:are )?(?:now )?open",
    re.I,
)
APPLY_BUTTON = re.compile(r"apply now|apply today|apply for incubation", re.I)
CLOSED = re.compile(
    r"applications? (?:are |is )?(?:now )?closed|registrations? (?:are |is )?(?:now )?closed|"
    r"intake (?:is )?closed|call (?:is )?closed|no longer accepting|(?:will )?open(?:s|ing)? soon",
    re.I,
)
DEADLINE_WORDS = r"(?:last date|deadline|apply (?:by|before)|closes on|closing date|due date)"
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}
DATE_PATTERNS = [
    # 15 October 2026, 15th Oct 2026, 15 Oct, 2026
    re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})"),
    # October 15, 2026
    re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"),
    # 15-10-2026, 15/10/2026, 15.10.2026 (day first, as written in India)
    re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})"),
]


def parse_date(text: str) -> dt.date | None:
    for i, pat in enumerate(DATE_PATTERNS):
        m = pat.search(text)
        if not m:
            continue
        try:
            if i == 0:
                day, mon, year = (
                    int(m.group(1)),
                    MONTHS.get(m.group(2)[:3].lower()),
                    int(m.group(3)),
                )
            elif i == 1:
                mon, day, year = (
                    MONTHS.get(m.group(1)[:3].lower()),
                    int(m.group(2)),
                    int(m.group(3)),
                )
            else:
                day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if mon:
                return dt.date(year, mon, day)
        except ValueError:
            continue
    return None


def deadlines(text: str) -> list[dt.date]:
    out = []
    for m in re.finditer(DEADLINE_WORDS, text, re.I):
        d = parse_date(text[m.end() : m.end() + 40])
        if d:
            out.append(d)
    return out


def _snippet(text: str, m: re.Match) -> str:
    return text[max(0, m.start() - 60) : m.end() + 60].strip()


def classify_intake(pages: list[tuple[str, str]], apply_url: str | None, today: dt.date) -> dict:
    """pages: (url, visible text). Returns status, deadline and the phrases that decided it."""
    evidence, dates, opened, closed, button = [], [], False, False, False
    for url, text in pages:
        for m in CLOSED.finditer(text):
            closed = True
            evidence.append({"url": url, "text": _snippet(text, m), "says": "closed"})
        for m in OPEN.finditer(text):
            opened = True
            evidence.append({"url": url, "text": _snippet(text, m), "says": "open"})
        for m in APPLY_BUTTON.finditer(text):
            button = True
            evidence.append({"url": url, "text": _snippet(text, m), "says": "apply button"})
        for d in deadlines(text):
            dates.append(d)
            evidence.append({"url": url, "text": f"deadline {d.isoformat()}", "says": "deadline"})
    upcoming = sorted(d for d in dates if d >= today)
    if upcoming:
        status, deadline = "open", upcoming[0]
    elif closed:
        status, deadline = "closed", None
    elif opened and not dates:
        status, deadline = "open", None
    elif dates:
        status, deadline = "closed", None  # every deadline found has passed
    elif button:
        status, deadline = "rolling", None
    elif apply_url:
        status, deadline = "apply_page", None
    else:
        status, deadline = "unknown", None
    return {
        "status": status,
        "deadline": deadline.isoformat() if deadline else None,
        "apply_url": apply_url,
        # Decisive phrases first: deadlines and open/closed wording before apply buttons.
        "evidence": sorted(evidence, key=lambda e: e["says"] == "apply button")[:4],
    }


@lru_cache
def load_intake() -> dict:
    return json.loads(DATA.read_text(encoding="utf8")) if DATA.exists() else {}


def current_intake(incubator_id: str, today: dt.date | None = None) -> dict | None:
    """The stored check for an incubator, or None if missing or older than STALE_DAYS."""
    rec = load_intake().get(incubator_id)
    if not rec or rec.get("status") in (None, "no_website", "unreachable", "robots_disallow"):
        return rec if rec else None
    today = today or dt.date.today()
    checked = dt.date.fromisoformat(rec["checked"])
    if (today - checked).days > STALE_DAYS:
        return {**rec, "status": "stale"}
    if rec.get("deadline") and dt.date.fromisoformat(rec["deadline"]) < today:
        return {**rec, "status": "closed", "note": "the deadline found has passed since the check"}
    return rec
