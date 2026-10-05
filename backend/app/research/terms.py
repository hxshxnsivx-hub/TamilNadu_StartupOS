"""From a founder's words to search terms the literature actually uses.

Founders describe ideas in everyday words ("brain waves", "physically
challenged"); papers, patents and trials use technical ones ("EEG",
"brain-computer interface", "locked-in syndrome"). This module expands the
everyday phrase into those terms with a small, reviewable lexicon, keeps the
founder's remaining content words, and builds one query per source.

The voice agent's language model can do this better for unusual ideas; when it
does, it passes its own `queries` and `elements` to the scan and this module is
bypassed. The lexicon is the offline floor, not the ceiling.
"""

from __future__ import annotations

import re

# everyday phrase -> technical terms. Matching is on whole words; longer phrases first.
LEXICON: dict[str, list[str]] = {
    "brain waves": ["EEG", "brain-computer interface"],
    "eeg": ["EEG"],
    "bci": ["brain-computer interface"],
    "brain computer interface": ["brain-computer interface"],
    "locked-in": ["locked-in syndrome"],
    "locked in": ["locked-in syndrome"],
    "nurse alert": ["nurse call system"],
    "nurse call": ["nurse call system"],
    "brain wave": ["EEG", "brain-computer interface"],
    "brain signals": ["EEG", "neural interface"],
    "mind control": ["brain-computer interface"],
    "thought": ["brain-computer interface"],
    "physically challenged": ["motor disability", "paralysis", "assistive technology"],
    "paralysed": ["paralysis", "locked-in syndrome"],
    "paralyzed": ["paralysis", "locked-in syndrome"],
    "bedridden": ["immobile patients", "assistive technology"],
    "disabled": ["disability", "assistive technology"],
    "cannot speak": ["augmentative and alternative communication"],
    "medication": ["medication management"],
    "medicine dose": ["medication dosage"],
    "eye movement": ["eye tracking"],
    "blind": ["visual impairment", "assistive technology"],
    "deaf": ["hearing impairment"],
    "sign language": ["sign language recognition"],
    "elderly": ["older adults"],
    "old people": ["older adults"],
    "heart": ["cardiac"],
    "sugar": ["diabetes"],
    "farmers": ["smallholder agriculture"],
    "crop disease": ["plant disease detection"],
    "soil": ["soil sensing"],
    "water saving": ["water use efficiency"],
    "drone": ["unmanned aerial vehicle"],
    "electric vehicle": ["electric vehicle"],
    "battery": ["lithium-ion battery"],
    "solar": ["photovoltaic"],
    "plastic": ["plastic waste"],
    "loan": ["credit access"],
    "fabric": ["textile"],
    "cloth": ["textile"],
}
# Terms specific enough to anchor a search; broad ones only add noise to short queries.
SPECIFIC = {
    "EEG",
    "brain-computer interface",
    "neural interface",
    "locked-in syndrome",
    "eye tracking",
    "augmentative and alternative communication",
    "sign language recognition",
    "plant disease detection",
    "soil sensing",
    "photovoltaic",
    "lithium-ion battery",
    "unmanned aerial vehicle",
    "medication management",
    "medication dosage",
    "nurse call system",
}
# Fallback when no papers can be searched: the fields a technical term belongs to.
TERM_FIELDS = {
    "EEG": ["Neuroscience", "Engineering"],
    "brain-computer interface": ["Neuroscience", "Computer Science", "Engineering"],
    "neural interface": ["Neuroscience", "Engineering"],
    "locked-in syndrome": ["Medicine", "Neuroscience"],
    "paralysis": ["Medicine"],
    "motor disability": ["Medicine", "Health Professions"],
    "assistive technology": ["Health Professions", "Engineering"],
    "augmentative and alternative communication": ["Health Professions", "Psychology"],
    "medication management": ["Medicine", "Pharmacology, Toxicology and Pharmaceutics"],
    "medication dosage": ["Medicine", "Pharmacology, Toxicology and Pharmaceutics"],
    "eye tracking": ["Computer Science", "Engineering"],
    "visual impairment": ["Medicine", "Health Professions"],
    "older adults": ["Medicine", "Health Professions"],
    "nurse call system": ["Nursing", "Health Professions"],
    "smallholder agriculture": ["Agricultural and Biological Sciences"],
    "plant disease detection": ["Agricultural and Biological Sciences", "Computer Science"],
    "soil sensing": ["Agricultural and Biological Sciences", "Engineering"],
    "photovoltaic": ["Energy", "Engineering"],
    "lithium-ion battery": ["Energy", "Engineering"],
    "plastic waste": ["Environmental Science"],
    "credit access": ["Economics, Econometrics and Finance"],
    "textile": ["Materials Science", "Engineering"],
}
HEALTH_TERMS = re.compile(
    r"patient|medic|health|hospital|clinic|disab|paraly|disease|therapy|diagnos|eeg|brain|"
    r"cardiac|diabetes|elderly|older adults|surgery|drug|nurse|rehab",
    re.I,
)
STOP = {
    "a",
    "able",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "be",
    "been",
    "being",
    "build",
    "by",
    "can",
    "change",
    "changes",
    "could",
    "develop",
    "developing",
    "development",
    "for",
    "from",
    "has",
    "have",
    "help",
    "helps",
    "how",
    "i",
    "idea",
    "in",
    "into",
    "is",
    "it",
    "its",
    "make",
    "making",
    "may",
    "me",
    "my",
    "new",
    "of",
    "on",
    "or",
    "our",
    "platform",
    "product",
    "project",
    "system",
    "systems",
    "that",
    "the",
    "their",
    "them",
    "these",
    "this",
    "those",
    "through",
    "to",
    "use",
    "used",
    "using",
    "via",
    "want",
    "we",
    "will",
    "with",
    "without",
    "would",
}


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z\-]+", text.lower())


def expand(text: str) -> tuple[list[str], list[str]]:
    """(technical terms from the lexicon, remaining content words)."""
    low = f" {text.lower()} "
    technical: list[str] = []
    for phrase in sorted(LEXICON, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            for t in LEXICON[phrase]:
                if t not in technical:
                    technical.append(t)
            low = re.sub(rf"\b{re.escape(phrase)}\b", " ", low)
    rest = [w for w in _words(low) if w not in STOP and len(w) > 3]
    seen: set[str] = set()
    content = [w for w in rest if not (w in seen or seen.add(w))]
    return technical, content


def build_queries(text: str) -> dict[str, str]:
    """Short, specific queries: search engines rank better on a few precise terms."""
    technical, content = expand(text)
    specific = [t for t in technical if t in SPECIFIC]
    broad = [t for t in technical if t not in SPECIFIC]
    papers = " ".join(specific[:3] + broad[:2] + content[:2]) or text
    trials = " ".join(specific[:2] + broad[:1]) or " ".join(content[:3]) or text
    projects = " ".join(specific[:2]) or " ".join((broad + content)[:3]) or text
    return {
        "papers": papers,
        "trials": trials,
        "projects": projects,
        "patents": papers,
        "local": " ".join(content + technical),
    }


def fields_from_terms(text: str) -> list[str]:
    technical, _ = expand(text)
    seen: list[str] = []
    for t in technical:
        for f in TERM_FIELDS.get(t, []):
            if f not in seen:
                seen.append(f)
    return seen


def is_health(text: str) -> bool:
    return bool(HEALTH_TERMS.search(text))
