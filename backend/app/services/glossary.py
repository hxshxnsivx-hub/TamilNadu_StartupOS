"""Startup-domain glossary for translation term-preservation (Task 1.5.3).

Each entry gives the term in English / Tamil / Hindi. During translation the
source-language term is masked with a sentinel, the sentence is translated, then
the sentinel is restored with the *target*-language term — so "funding" never
comes back mistranslated. Terms that must stay verbatim (DPIIT, GST…) simply use
the same string in all three languages.
"""

from __future__ import annotations

# term_id: {lang: surface form}
GLOSSARY: list[dict[str, str]] = [
    {"en": "funding", "ta": "நிதியளிப்பு", "hi": "फंडिंग"},
    {"en": "scheme", "ta": "திட்டம்", "hi": "योजना"},
    {"en": "startup", "ta": "தொடக்க நிறுவனம்", "hi": "स्टार्टअप"},
    {"en": "roadmap", "ta": "வழித்தடம்", "hi": "रोडमैप"},
    {"en": "investor", "ta": "முதலீட்டாளர்", "hi": "निवेशक"},
    {"en": "eligibility", "ta": "தகுதி", "hi": "पात्रता"},
    {"en": "revenue", "ta": "வருவாய்", "hi": "राजस्व"},
    {"en": "milestone", "ta": "மைல்கல்", "hi": "मील का पत्थर"},
    # verbatim across languages (acronyms / proper nouns)
    {"en": "DPIIT", "ta": "DPIIT", "hi": "DPIIT"},
    {"en": "GST", "ta": "GST", "hi": "GST"},
    {"en": "GSTIN", "ta": "GSTIN", "hi": "GSTIN"},
    {"en": "B2B", "ta": "B2B", "hi": "B2B"},
    {"en": "TANSEED", "ta": "TANSEED", "hi": "TANSEED"},
    {"en": "MSME", "ta": "MSME", "hi": "MSME"},
]
