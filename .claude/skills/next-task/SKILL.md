---
name: next-task
description: Take the next open subtask from .kiro/specs/tamil-nadu-startupos/tasks.md (or a given id), have task-worker build it, have task-reviewer check it as maintainer, loop rework until it passes (at most 3 reviews), then commit each file separately, push the branch and open a PR. Usage: /next-task [subtask id]
---

# Next task: build, review, rework, ship

One subtask per run. The worker builds; the reviewer, a separate agent with no write tools,
decides whether it is up to the mark. Nothing reaches `Main`, and nothing is merged: the user
merges the PR.

## 1. Pick the subtask

- If an id was passed (e.g. `/next-task 2.3.4`), use it.
- Otherwise read `.kiro/specs/tamil-nadu-startupos/tasks.md` and take the first `[ ]` subtask by
  priority (P0 before P1 before P2, then file order) whose parent task's **Dependencies** are
  all `[x]`.
- If no subtask has a marker note yet (` — done:` / ` — open:`), the list has not been audited:
  stop and tell the user to run `/audit-tasks` first.
- Tell the user which subtask was picked and why, in one line.

## 2. Branch

Start from a clean tree. Create `task/<id>-<short-slug>` from the working branch
(`feature/bank-loan-routing` unless the user names another). Never `Main`.

## 3. Build

Launch the `task-worker` agent with the subtask id. If it stops on a blocker (an open
dependency, or the task needs something paid), skip to step 6 and report the blocker; do not
commit. Keep the agent's id for rework.

## 4. Review, rework, repeat (at most 3 reviews)

Launch the `task-reviewer` agent with the subtask id. Read the first line of its result:

- `VERDICT: PASS`: go to step 5.
- `VERDICT: REWORK`: send the findings, verbatim, to the same worker with SendMessage, so it
  keeps its context, and review again with a fresh `task-reviewer`.

After the third REWORK, stop. Do not commit. Leave the changes in the working tree on the task
branch, and report the remaining findings so the user can decide.

## 5. Ship

- Re-run from `backend/`: `python -m pytest -q -p no:cacheprovider`. It must pass.
- Commit **each changed file as its own commit**, code before tests before `tasks.md`, each
  message saying what that file's change does, each ending with the attribution line from the
  session's git instructions.
- Push the branch and open a PR into the working branch (`gh pr create` if `gh` is installed;
  otherwise give the compare URL
  `https://github.com/hxshxnsivx-hub/TamilNadu_StartupOS/compare/<base>...<branch>?expand=1`).
  The PR body says the subtask, what changed, the test result and the reviewer's PASS note. Do
  not merge.

## 6. Report

Subtask id and title; outcome (shipped, blocked, or stopped after 3 reviews); number of review
rounds and what each rework fixed; the commits; the PR link; the next open subtask.
