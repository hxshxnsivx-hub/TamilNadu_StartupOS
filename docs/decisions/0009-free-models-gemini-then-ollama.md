# 0009. Free models write and speak the mentor's replies: Gemini, then Ollama

**Status:** Accepted · **Date:** 2026-10-13

## Context

The product owner cannot pay for APIs (only a Claude Pro chat plan, which does not cover an
app's backend). Without a model, the mentor spoke English templates, which sounds scripted.
Every reply should be written for the founder's situation, in their language, and spoken in
one mentor voice. The browser's own voice is not acceptable.

## Decision

- **One interface, several providers** (`app/agents/providers.py`), tried in
  `LLM_ORDER` (default `anthropic,gemini,ollama`): each that is configured and whose circuit
  breaker is closed. A quota error (HTTP 429) or any failure moves the turn to the next;
  templates are the last resort. The conversation is stored in one format whatever model
  wrote it, so a session can move between providers mid-conversation; Gemini's own steps are
  kept verbatim because it needs them back.
- **Gemini API, free tier,** writes the replies and calls the research tools itself, like
  Claude would (`gemini-3.8-flash`, low thinking for speed). The review panel's seats use
  `gemini-3.5-flash-lite`; a seat over quota falls back to its rule.
- **Ollama on the owner's machine** (`gemma3:4b`) is the offline backup. A small model on a
  CPU is slow and unreliable with tools, so it never calls them: the code runs the turn
  (scan, novelty, panel, roadmap) and builds the reply, and Ollama rewords it in the founder's
  language and a mentor's tone. It never sits on the review panel.
- **The fact check applies to every model** (decision 0005): each sentence is checked before
  it is spoken; a reworded reply that loses everything falls back to the code's own reply.
- **The voice comes from the server only:** Sarvam if paid for, else Gemini text-to-speech
  (`gemini-3.8-flash-tts`, same key; one voice per language and a calm mentor style), else the
  Parler recordings of fixed sentences. With none of them the sentence is shown, not spoken.
  Gemini audio is cached by text, language, voice and style, so a repeated sentence costs one
  request ever. To spend fewer requests on a free quota, the first sentence of a reply is
  spoken at once and the sentences that follow while it plays travel together.

## Options considered

- **Ollama only:** private and free without limits, but slow on a CPU, weaker in Tamil, and no
  model good enough to call tools reliably. Kept as the backup.
- **Groq or OpenRouter free models:** free keys, but weaker Tamil and changing free lists.
- **Parler recordings for model-written sentences:** too slow to make live on a laptop CPU
  (8–50 times longer than the speech); kept for fixed sentences when Gemini cannot speak.
- **The browser's own voice:** rejected by the product owner.

## Consequences

- Free-tier limits are per Google Cloud project and shown only in AI Studio; when a limit is
  reached the turn moves to Ollama and the voice to the recordings, without breaking.
- On the free tier Google may use the text to improve its products; founders should be told
  before a pilot. Private mode still limits which research sources are searched, but the
  conversation itself goes to whichever model is configured.
- Ollama replies take seconds to tens of seconds on a CPU; Tamil from a 4B model is weaker
  than Gemini's.
- Listening still uses the browser's recognition (or Sarvam with a key); Gemini transcription
  is a possible next step.
