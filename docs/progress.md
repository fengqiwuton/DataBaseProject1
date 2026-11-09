# Implementation ledger — docs/implementation-plan.md

- 2026-10-24: User approved existing technical route and requested implementation. Continue autonomously through checks and packaging.
- Ruling: Native implementation inside Project1_v0; no Git repository exists, so no worktree or commits. Original files remain outside implementation scope.
- Ruling: Use Java 17 language target on installed JDK 20, build without Maven as Maven is absent; keep pom.xml as alternate.
- Ruling: Use the report's disclosed Longgang 梨园 mapping and atomic exit expansion as configurable defaults; no invented fare data.
- Preflight: importer table names feed repository, queries and tests; service action allowlist shared by CLI and web; routing consumes transactionally consistent adjacency rows. No conflicting interfaces identified.

- Task 1 complete: Python tests 3/3; real PostgreSQL two full import runs and SQL examples pass (logs .runtime/import-first.log, import-second.log, queries.log).
- Task 2 complete: real IntegrationTest passes Q1–Q7, identity, CRUD, batch insert/remove, rollback, simultaneous insert and cleanup to 439.
- Task 3 complete: RouterTest covers 6 scenarios including minimum-transfer stop tie-break and disconnected/multi-source routes.
- Task 4 implementation complete: WebTest passes homepage/API and GET/token/origin write guards; packaged CLI action and interactive exit smoke pass.
- Environment correction: installed PostgreSQL executable actually reports 12.1, despite parent folder named 12.6. SQL tested on 12.1; recommended production deployment should use a maintained release.
- Windows correction: Start-Process -Wait waits for server descendants; use hidden pg_ctl plus parent WaitForExit(30000). Java -D option must be quoted in PowerShell.
- Task 5 in progress: expanded verification, visual review, docs, package and fresh code review.
- Final review: I1 refresh replay and I2 construction-only zero-edge operating route fixed with failing-then-passing regressions; full suite green including 3 Node scenarios and both route modes.
- Final minors retained: missing Content-Type status code; startup complete-schema check; uniform batch membership attributes. Effects disclosed in verification.md.
- Benchmark correction: fresh psql processes do not warm per-session PL/pgSQL caches; benchmark now keeps each query's 30 samples in a single session, retaining the cold first call separately. No code performance speedup claim is inferred.
- Visual QA: headless browser launch was rejected by automatic approval policy; no bypass attempted. HTTP/static/DOM checks remain available.
- Task 5 complete: 57-file source/runtime ZIP built; extracted into a new path containing spaces, JAR help/Q1 and Python suite all pass. Package excludes runtime databases and private config. No Git commits apply in this non-repository directory.
- User-reported Windows PowerShell startup failure: reproduced all five scripts failing the 5.1 native parser because UTF-8 source lacked BOM. Converted all five to UTF-8 BOM and added tests/test_powershell.py; both encoding and real-parser tests observed failing before correction and passing afterwards. Earlier verification used pwsh7 and did not establish 5.1 source compatibility.
