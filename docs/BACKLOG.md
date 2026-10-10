# Backlog

Work that is decided but parked. Each item says why it waits and what unblocks it.

## Flagged

### Free mentor voice and languages (flagged 2026-10-10)

**Why parked:** no budget for paid APIs. Only a Claude Pro chat plan is available, and it does
not power the app's backend. `ANTHROPIC_API_KEY` and `SARVAM_API_KEY` stay unset, so `/talk`
runs offline: template replies in English and the browser's default voice.

**Free fixes, ready to build:**

1. **Best free voice.** Pick the best neural voice the browser offers per language: Microsoft
   Edge exposes natural Tamil, Hindi and Indian-English voices to web pages at no cost; Chrome
   has some Google voices. Let the founder choose a voice; tune pace and the pause between
   sentences; suggest Edge.
2. **Offline replies in Tamil and Hindi.** Translate the fixed templates (greeting, the 19
   questions, acknowledgements, evidence, novelty and review-panel summaries) so the whole
   conversation follows the founder's language. Titles and names stay in English. Needs a
   native-speaker review before founders hear it.
3. **One language setting** that drives both the browser's recognition and its voice.

**Later, free model options** (an adapter behind `app/services/llm.py`):

- Google Gemini API free tier: rate-limited, good Tamil and Hindi, needs a Google key but no
  payment.
- A local model through Ollama: free and offline, Tamil quality varies, needs a capable machine.

**Already built and waiting for keys:** Claude conversation and review-panel seats, Sarvam
voice and listening (decision 0008). They switch on by themselves when the keys are set.

## Waiting on something

| Item | Waits on |
|---|---|
| Database store tested live, migration `0004` applied | correct local PostgreSQL credentials in `backend/.env` |
| Background jobs (Phase 2b); `backend/app/agents/results.py` holds its first part | a fresh attempt; earlier attempts were interrupted |
| Pushing `feature/bank-loan-routing` | the owner's go-ahead |
| Weekly data jobs opening pull requests | "Allow GitHub Actions to create and approve pull requests" in repository settings |
| The uncommitted frontend theme removal (since 2026-10-02) | the owner's decision to commit it |
