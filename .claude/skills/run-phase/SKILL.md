---
name: run-phase
description: Work through every open task of one phase of docs/specs/TASKS.md without stopping between tasks: build → maintainer review → rework for each task, committing each file separately and pushing each pass, parking what cannot be finished, and opening one PR at the end. Usage: /run-phase <phase number>
---

# Run a whole phase, unattended

The owner asked for this to run **without pausing for permission between tasks**. Do not ask
"shall I continue?", do not wait after a task ships, and do not end the turn while open,
unblocked tasks remain in the phase. Report progress in one line per task.

## 0. Branch

Start from a clean tree. If `run/phase-<n>` exists, switch to it and continue where it left off.
Otherwise create it from the branch that holds the current `docs/specs/TASKS.md`. Never `Main`.

## 1. Order the tasks

List the phase's `[ ]` tasks (`#### N.M.T` headings) in `docs/specs/TASKS.md`. Skip `[w]`, `[d]`
and `[x]` tasks. Order them so that a task runs after any task its When names; otherwise file
order. A task whose When names something unbuildable (`[w]`, `[d]`) still runs for the parts that
do not depend on it.

## 2. Loop until the phase is finished

For each task:

1. **Build** with `task-worker` (task id).
2. **Review** with a fresh `task-reviewer`. On `VERDICT: REWORK`, send the findings verbatim to
   the same worker (SendMessage), then review again. At most 3 reviews.
3. **On PASS:** run the full test suite from `backend/`; it must pass. Commit each changed file
   as its own commit (code, then tests, then `docs/specs/TASKS.md`), each message saying what
   that file's change does and ending with the attribution line from the session's git
   instructions. Push. One progress line.
4. **Park** (blocked, or still REWORK after 3 reviews): move any changes to `wip/<task id>`
   (`git switch -c`, commit, push, switch back), note the reason under the task in
   `docs/specs/TASKS.md`, commit that, push, and move on.

Stop early only if the suite fails on the branch itself and one worker attempt cannot fix it.

## 3. Finish

Open one PR from `run/phase-<n>` (`gh pr create` if `gh` is installed; otherwise give the compare
URL `https://github.com/hxshxnsivx-hub/TamilNadu_StartupOS/compare/<base>...run/phase-<n>?expand=1`).
Do not merge.

Report: tasks shipped with their commits, tasks parked with reasons and `wip/` branches, tasks
left for decisions or waits, and the PR link.
