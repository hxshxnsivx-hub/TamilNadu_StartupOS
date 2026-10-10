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
from functools import lru_cache

# everyday phrase -> technical terms. Matching is on whole words; longer phrases first.
LEXICON: dict[str, list[str]] = {
    "herbal tea": ["herbal tea"],
    "tea infusions": ["herbal tea"],
    "tea infusion": ["herbal tea"],
    "tea": ["tea"],
    "hibiscus": ["Hibiscus sabdariffa"],
    "mint": ["Mentha"],
    "jasmine": ["Jasminum sambac"],
    "malli": ["Jasminum sambac"],
    "coconut": ["coconut"],
    "virgin coconut oil": ["virgin coconut oil"],
    "banana": ["banana"],
    "plantain": ["banana"],
    "turmeric": ["turmeric"],
    "t-shirt": ["knitted apparel"],
    "t-shirts": ["knitted apparel"],
    "knitwear": ["knitted apparel"],
    "yarn": ["yarn"],
    "spinning mills": ["yarn spinning"],
    "solar inverter": ["photovoltaic inverter"],
    "solar inverters": ["photovoltaic inverter"],
    "pump motors": ["electric motor pump"],
    "dry run": ["pump dry running protection"],
    "dry-run": ["pump dry running protection"],
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
    "herbal tea",
    "Hibiscus sabdariffa",
    "Mentha",
    "Jasminum sambac",
    "virgin coconut oil",
    "knitted apparel",
    "photovoltaic inverter",
    "pump dry running protection",
    "turmeric",
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
    "herbal tea": ["Agricultural and Biological Sciences"],
    "tea": ["Agricultural and Biological Sciences"],
    "Hibiscus sabdariffa": ["Agricultural and Biological Sciences"],
    "Mentha": ["Agricultural and Biological Sciences"],
    "Jasminum sambac": ["Agricultural and Biological Sciences"],
    "coconut": ["Agricultural and Biological Sciences"],
    "virgin coconut oil": ["Agricultural and Biological Sciences"],
    "banana": ["Agricultural and Biological Sciences"],
    "turmeric": ["Agricultural and Biological Sciences"],
    "knitted apparel": ["Materials Science", "Engineering"],
    "yarn": ["Materials Science"],
    "yarn spinning": ["Materials Science", "Engineering"],
    "photovoltaic inverter": ["Energy", "Engineering"],
    "electric motor pump": ["Engineering"],
    "pump dry running protection": ["Engineering"],
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
    "made",
    "buying",
    "sell",
    "sells",
    "selling",
    "brand",
    "brands",
    "start",
    "starting",
    "want",
    "wants",
    "make",
    "makes",
    "making",
    "using",
    "proper",
    "directly",
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
    "via",
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


@lru_cache
def public_vocabulary() -> frozenset[str]:
    """Words that may leave the platform in a search query.

    The lexicon, the research-field names and the words of Vanigam's own domain
    registry: all public, all generic. A founder's brand names, invented product
    names, people and places are not in it, so they are never sent to a source.
    """
    words: set[str] = set()
    for phrase, terms in LEXICON.items():
        words |= set(_words(phrase))
        for t in terms:
            words |= set(_words(t.lower()))
    for fields in TERM_FIELDS.values():
        for f in fields:
            words |= set(_words(f.lower()))
    try:
        from app.planner import registry

        reg = registry.load()
        proper: set[str] = set()  # places and names, capitalised mid-sentence
        for d in reg["domains"].values():
            text = f"{d['label']}. {d['summary']}"
            words |= set(_words(text.lower()))
            proper |= {m.lower() for m in re.findall(r"(?<![.!?(]\s)(?<!^)\b[A-Z][a-z]{2,}", text)}
        words -= proper
        for c in reg["categories"].values():
            words |= set(_words(c["label"].lower()))
    except Exception:  # the registry is optional here; the lexicon still applies
        pass
    return frozenset(w for w in words if len(w) > 2 and w not in STOP and not _is_place(w))


def _is_place(word: str) -> bool:
    from app.elicitation.places import find_district

    return find_district(word) is not None


def scrub(query: str, founder_text: str = "") -> str:
    """Make a query written by the agent's model safe to send.

    Drops numbers and place names, and any word the founder said that is not in
    the public vocabulary; keeps the model's own technical terms. At most 8 words.
    """
    said = set(_words(founder_text.lower()))
    vocab = public_vocabulary()
    keep = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9-]*", query):
        low = w.lower()
        if _is_place(low) or (low in said and low not in vocab):
            continue
        keep.append(w)
    return " ".join(keep[:8])


def build_queries(text: str) -> dict[str, str]:
    """Short, specific queries: search engines rank better on a few precise terms.

    Only technical terms and public-vocabulary words are used, never the
    founder's sentence. An empty query means "nothing safe to send": the source
    is reported as not searched rather than sent the idea text.
    """
    technical, content = expand(text)
    vocab = public_vocabulary()
    content = [w for w in content if w in vocab]
    specific = [t for t in technical if t in SPECIFIC]
    broad = [t for t in technical if t not in SPECIFIC]
    papers = " ".join(specific[:3] + broad[:2] + content[:2])
    trials = " ".join(specific[:2] + broad[:1]) or " ".join(content[:3])
    projects = " ".join(specific[:2]) or " ".join((broad + content)[:3])
    return {
        "papers": papers,
        "trials": trials,
        "projects": projects,
        "patents": papers,
        "local": " ".join(content + technical),
    }


def term_groups(text: str) -> list[tuple[str, list[str]]]:
    """The idea's parts: (the founder's phrase, its technical terms), longest phrase first.

    "communication through brain waves for medication change" gives
    ("brain waves", ["EEG", "brain-computer interface"]), ("medication", [...]).
    The phrases are lexicon keys: public words, safe to show and to send.
    """
    low = f" {text.lower()} "
    groups: list[tuple[str, list[str]]] = []
    seen: set[tuple[str, ...]] = set()
    for phrase in sorted(LEXICON, key=len, reverse=True):
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            terms = LEXICON[phrase]
            if tuple(terms) not in seen:
                seen.add(tuple(terms))
                groups.append((phrase, list(terms)))
            low = re.sub(rf"\b{re.escape(phrase)}\b", " ", low)
    return groups


def or_query(terms: list[str]) -> str:
    """One part of an idea as a search: its technical names, any of them."""
    quoted = [f'"{t}"' if " " in t or "-" in t else t for t in terms]
    return quoted[0] if len(quoted) == 1 else f"({' OR '.join(quoted)})"


def element_query(text: str) -> str:
    """A part of an idea, as given by the founder or the model, as a safe search."""
    technical, content = expand(text)
    if technical:
        return or_query(technical[:4])
    vocab = public_vocabulary()
    return " ".join([w for w in content if w in vocab][:3])


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
