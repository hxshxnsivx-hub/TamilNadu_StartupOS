---
name: audit-tasks
description: Mark every subtask in .kiro/specs/tamil-nadu-startupos/tasks.md as done, open or superseded from the actual code, one phase per task-auditor agent, then commit the result on its own branch and open a PR. Run before /next-task, and again whenever the list drifts.
---

# Audit tasks.md

Makes the checkboxes in `.kiro/specs/tamil-nadu-startupos/tasks.md` true, so /next-task picks
only work that is genuinely open.

## Steps

1. **Branch.** Start clean (`git status` shows no changes to `tasks.md`). Create
   `chore/tasks-audit-<YYYY-MM-DD>` from the working branch (`feature/bank-loan-routing` unless
   the user names another). Never work on `Main`.
2. **Audit in parallel.** The file has five phases (`## PHASE 1` to `## PHASE 5`). Launch one
   `task-auditor` agent per phase, all in the same message, each told its phase number and
   heading. If the user passed a phase number as an argument, audit only that phase.
3. **Check the result.** When all have reported:
   - `git diff --stat` touches only `tasks.md`.
   - Every subtask line in the audited phases carries `[x]`, `[ ]` or `[~]` and a note.
   - Spot-check three `[x]` lines by opening their evidence path. If one does not hold up, set
     it back to `[ ]` and say so in the summary.
4. **Summary block.** Directly under the `## Overview` paragraph, write or replace one block:

   ```
   **Status (audited YYYY-MM-DD):** N done · N open · N superseded. Next up: <ids>.
   ```

5. **Commit and PR.** One commit for `tasks.md`, message `Tasks: audit status against the code
   (YYYY-MM-DD)`, ending with the attribution line from the session's git instructions. Push
   the branch. Open a PR into the working branch (`gh pr create` if `gh` is installed;
   otherwise give the user the compare URL
   `https://github.com/hxshxnsivx-hub/TamilNadu_StartupOS/compare/<base>...<branch>?expand=1`).
   Do not merge it.

## Report

Counts per phase, the superseded items with their reasons, the first ten open subtasks in
priority order, and the PR link.
