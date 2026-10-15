# 0008. The mentor's voice and listening use Sarvam AI, through the server

**Status:** Accepted · **Date:** 2026-10-10

## Context

The first voice used the browser's own speech: flat, often no Tamil voice, no control of pace,
and English replies only. Founders should hear a warm mentor in Tamil, English or Hindi, the
way they mix them, with little delay.

## Decision

- **Service:** Sarvam AI, chosen by the product owner: built for Indian languages and
  code-mixed speech, with data processed in India. Text-to-speech with Bulbul
  (`bulbul:v3`, one speaker, `shubh` by default, for every language so the mentor's voice stays
  the same; pace 0.95). Speech-to-text with Saaras (`saaras:v4`), language auto-detected,
  biased toward startup words with up to 50 key terms (DPIIT, TANSEED, FSSAI, lakh, …).
- **Through the server:** the browser calls `/api/v1/voice/speak` and `/voice/transcribe`;
  the Sarvam key never reaches the browser. Audio is passed through, never stored; only the
  synthesised audio of repeated sentences is cached (by a hash of text, language and voice).
- **Latency without streaming connections:** Sarvam's documented REST endpoints are used. Each
  sentence's audio is requested the moment the sentence arrives, so the next is ready while
  the current one plays. The browser detects the end of the founder's speech (800 ms of
  quiet, adapting to room noise) and a cached acknowledgement ("சரி.", "अच्छा।", "Okay.")
  plays at once while the words are transcribed and the reply prepared.
- **The founder's language:** each turn carries the detected language; Claude replies in it,
  mixing English words the way the founder does. The ack event tells the browser which
  language to speak in.
- **Degrade, never break:** without a key, or when Sarvam fails for a sentence, the browser's
  voice speaks instead; the caption always shows the words.

## Options considered

- **ElevenLabs:** most expressive, one identical voice in all three languages; data abroad,
  and listening would need another service.
- **Azure or Google Cloud:** fine pace and pause control; a different voice per language.
- **Self-hosted open models (AI4Bharat):** no per-minute cost, but a GPU server to run.
- **Sarvam's streaming (WebSocket) connections:** lower latency still, but their message
  format is not in the public API reference; adopt when it is.

## Consequences

- With a key, first audio follows the first sentence by one synthesis call; acknowledgements
  are instant from cache.
- Without a Claude key, replies stay English (the offline templates are English only), and the
  voice speaks them in English.
- Each utterance is transcribed after the founder stops, so there are no live partial captions
  in this mode; the browser-voice mode still shows them.
