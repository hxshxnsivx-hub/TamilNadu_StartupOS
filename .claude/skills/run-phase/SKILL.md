---
name: run-phase
description: Work through every open subtask of one phase of .kiro/specs/tamil-nadu-startupos/tasks.md without stopping between tasks. Audits the phase if needed, then build → maintainer review → rework for each subtask, committing and pushing each pass, parking failures, and opening one PR at the end. Usage: /run-phase <phase number>
---

# Run a whole phase, unattended

The user has asked for this to run **without pausing for permission between tasks**. Do not
ask "shall I continue?", do not wait after a task ships, and do not end the turn while open,
unblocked subtasks remain in the phase. Report progress in one line per task as you go.

## 0. Branch

Start from a clean tree. If `phase/<n>` exists (locally or on origin), switch to it and continue
where it left off. Otherwise create `phase/<n>` from the working branch
(`feature/bank-loan-routing` unless the user names another). Never `Main`.

## 1. Audit the phase if it has not been

If the phase's subtask lines carry no ` — done:` / ` — open:` / ` — superseded:` notes, run one
`task-auditor` agent for this phase. Check the diff touches only `tasks.md`, commit it
(`Tasks: audit phase <n> against the code`), push.

## 2. Loop until the phase is finished

Repeat:

1. **Pick** the first `[ ]` subtask in the phase by priority (P0, P1, P2, P3, then file order)
   whose parent task's Dependencies are all `[x]` and that is not already parked this run. If
   none, go to step 3.
2. **Build** with `task-worker` (subtask id). If it reports a blocker, park it (below).
3. **Review** with a fresh `task-reviewer`. On `VERDICT: REWORK`, send the findings verbatim to
   the same worker with SendMessage, then review again. At most 3 reviews.
4. **On PASS:** run `python -m pytest -q -p no:cacheprovider` from `backend/`; it must pass.
   Commit each changed file as its own commit (code, then tests, then `tasks.md`), each message
   saying what that file's change does and ending with the attribution line from the session's
   git instructions. Push `phase/<n>`. One progress line to the user. Next iteration.
5. **Park** (blocked, needs something paid, or still REWORK after 3 reviews): if there are
   changes, move them to `wip/<id>` without losing them: `git switch -c wip/<id>`, commit all,
   push, `git switch phase/<n>`. Then set the subtask's note in `tasks.md` to
   ` — open: parked: <one-clause reason>; see wip/<id>` (or ` — superseded: <reason>` if it
   needs a paid service), commit that line, push. Next iteration.

Stop the loop early only if the full test suite fails on `phase/<n>` itself and one worker
attempt cannot fix it; then report and stop.

## 3. Finish

Update the status line under `## Overview` in `tasks.md`, commit, push. Open one PR from
`phase/<n>` into the working branch (`gh pr create` if `gh` is installed; otherwise give the
compare URL `https://github.com/hxshxnsivx-hub/TamilNadu_StartupOS/compare/<base>...phase/<n>?expand=1`).
Do not merge.

Report: shipped subtasks with their commits, parked subtasks with reasons and `wip/` branches,
superseded subtasks, counts for the phase, and the PR link.
