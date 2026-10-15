# 0004. Only public vocabulary leaves the platform

**Status:** Accepted · **Date:** 2026-10-09

## Context

The prior-art scan sends search queries to OpenAlex, ClinicalTrials.gov, GitHub and patent
services. When no technical term was found, the query builder fell back to the founder's own
sentence, sending an unprotected idea to third parties.

## Decision

Outgoing queries contain only words from a public vocabulary: the lexicon's terms, research
field names, and the words of Vanigam's own domain registry, minus proper nouns and Tamil Nadu
place names (`public_vocabulary()` in `app/research/terms.py`). Queries written by the model are
cleaned the same way (`scrub()`). If nothing safe remains, the source is reported as *not
searched*. A session can be private (`private: true`): no external source is called.

## Options considered

- **Send the founder's text:** best recall, leaks the idea.
- **Lexicon terms only:** safest, but too few searches would run at all.

## Consequences

- Brand names, people and places never reach a third party.
- Recall drops for ideas described in words outside the vocabulary (for example "dryer",
  "copra"). The lexicon grows from logged weak searches (build spec 5.4).
