---
name: next-task
description: Take the next open task from docs/specs/TASKS.md (or a given id), have task-worker build it, have task-reviewer check it as maintainer, loop rework until it passes (at most 3 reviews), then commit each file separately, push and open a PR. Usage: /next-task [task id]
---

# Next task: build, review, rework, ship

One task per run, through every step without asking the user to confirm. To work through a
whole phase without stopping, use `/run-phase <n>` instead.

1. **Pick:** the given id, or the first `[ ]` task in `docs/specs/TASKS.md` (phase order, then
   file order) whose When names nothing still open. One line saying which and why.
2. **Branch:** `task/<id>-<slug>` from the branch holding the current task file. Never `Main`.
3. **Build** with `task-worker`. Keep its id.
4. **Review** with a fresh `task-reviewer`; on REWORK send the findings verbatim to the same
   worker and review again; at most 3 reviews, then stop and report without committing.
5. **Ship:** full test suite passes; one commit per changed file (code, tests, task file), each
   ending with the session's attribution line; push; PR into the base branch (`gh` if installed,
   else the compare URL). Do not merge.
6. **Report:** task, outcome, review rounds, commits, PR link, next open task.
