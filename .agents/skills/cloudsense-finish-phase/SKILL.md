---
name: cloudsense-finish-phase
description: Verifies and documents a CloudSense AI phase after implementation by running relevant checks, reviewing the diff, updating status documents, checking actual application behavior, and producing evidence-based acceptance results. Use after a phase implementation or before requesting phase completion.
---

# Finish and Verify a CloudSense AI Phase

1. Inspect `git diff --check`, `git status --short`, and the final diff. Verify that unrelated files, secrets, generated binaries, local databases, and personal configuration were not accidentally changed or committed.
2. Run the relevant automated tests. Run lint, type checks, frontend builds, and full tests when configured and reasonably available. Never claim a command passed unless it actually ran successfully.
3. If the UI changed and browser testing is available, run the application and verify the affected user flow with the browser. Capture a real screenshot only if supported. If browser testing is unavailable, clearly say it was not performed.
4. For data-related features, test empty input, malformed input, duplicates, boundary cases, authorization failure, and failure recovery where applicable.
5. Check feature acceptance criteria one by one. A page or route is not proof that the feature works.
6. Update `docs/PROJECT_STATUS.md` with accurate implemented/partial/broken/missing status, actual test evidence, and remaining blockers. Update relevant documentation and add an ADR when a significant design decision was made.
7. Report:
   A. What was inspected.
   B. Files changed and why.
   C. Acceptance criteria met/not met.
   D. Exact commands/tests and results.
   E. How to launch and verify.
   F. Outstanding issues and data/credential dependencies.
   G. Proposed next phase and why.
8. Suggest a commit message, but do not commit or push unless the user requested it.
9. Include five interview questions with concise model answers grounded only in what was actually built.
