# Rotate an API key

Keys in use: `ANTHROPIC_API_KEY`, `OPENALEX_API_KEY`, `PATENTSVIEW_API_KEY`, `GITHUB_TOKEN`, and
the database password. All are read from the environment (`backend/.env` locally); none belong
in the repository.

## When

A key was exposed (pasted in a chat, committed, shown in a log), a person with access leaves,
or the provider expires it.

## Steps

1. Create the new key in the provider's console.
2. Put it in the environment where the app runs (`backend/.env` locally, the secret store in
   deployment). Settings are read once at start-up, so restart the app.
3. Check that it works (below), then revoke the old key in the provider's console.
4. If the old key was committed, removing it from the latest commit is not enough: it remains in
   history. Revoking it (step 3) is what makes it harmless.

## Confirm

- Anthropic: a streamed turn ends with `done`.
- OpenAlex, GitHub, PatentsView: a new scan shows `ok` for papers, projects and patents.
