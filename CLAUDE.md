@AGENTS.md

## Main session: dispatch only (user rule, 2026-10-25)

The main session of this directory does not do the work itself. It only writes task files, dispatches them and moves the plan to the next step.

Scope: this section applies only to the interactive main session (the Archive Editor pane that talks to the user). A dispatched worker that was started with a task file is not the main session: it does the work its task file names (edit, test, commit as the task says) and does not dispatch other agents.

1. Do not edit code or content in the main session. A dispatched agent edits.
2. Do not run unit tests, validators or checks in the main session. A dispatched agent runs them.
3. Verification is always done by a different agent than the one that made the change. The main session does not decide that a change passes; it reads the verifier's report.
4. Dispatch through herdr panes (the `workers` tab, `tasks/claude-local.sh`, or the repo owner pane). Do not use an in-process subagent instead of herdr.
5. The main session may read files and reports, write task files, and talk to the user and the PM.
