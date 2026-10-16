---
name: cloudsense-start-phase
description: Starts one controlled CloudSense AI development phase by checking repository status, reading relevant project documentation, scoping changes, identifying risks and tests, and producing an implementation plan before code changes. Use at the start of each phase or when asked to plan a CloudSense AI change.
---

# Start a CloudSense AI Phase

1. Confirm the current workspace and repository root. Do not assume the user's Mac path is mounted into the current tool environment.
2. Read the persistent CloudSense workspace rules, `docs/PROJECT_STATUS.md` if present, `docs/PROJECT_SCOPE.md`, and the relevant phase prompt.
3. Run `git status --short` and inspect the current branch. Preserve all existing user changes. Do not reset, clean, or overwrite them.
4. Inspect only the source files and configuration relevant to the requested phase, expanding the scope only when evidence shows a dependency.
5. Produce an Implementation Plan **before coding** containing:
   - goal and explicit in-scope work;
   - files/modules to inspect and likely files to change;
   - current behavior and evidence;
   - schema/API/configuration changes, if any;
   - risks, data safety, security, and compatibility concerns;
   - tests and concrete acceptance criteria;
   - rollback approach;
   - questions or external requirements that genuinely block progress.
6. Create or update a task list with pending/in-progress/done states.
7. Stop and wait for the user's approval before editing code, changing schema, installing dependencies, or making external provider calls.
8. Do not ask for approval for harmless repository inspection already authorized by the request. Do not ask repeated questions already answered in project documentation.
9. If asked to perform Phase 1 audit, gather evidence from the actual database path, row counts where safe, SQL/aggregation code, API response, frontend mapping, prediction model loading, and tests. Do not guess at the dashboard's zero-value root cause.

## Completion of planning step
Return the plan and a concise list of required approvals. Do not report implementation complete before implementation starts.
