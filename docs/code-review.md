# Whole-project code review

Reviewed 2026-10-24. Scope: current all-new implementation in `Project1_v0`; no Git repository or diff is available. This is one consolidated review of production source and its verification evidence. No production files or database data were modified by this review.

## Assessment

**No Critical issue identified. Two Important issues require correction before delivery.** The six-table design, conservative source mapping, parameter binding, deferred station-position uniqueness, serialized topology writes, read-only route snapshot and the two routing objectives are coherent. No additional actionable importer/SQL transaction corruption issue was found in the inspected scope.

## Important findings

### I1 — The result-panel refresh button can delete a different record or repeat another mutation

- Location: `app/src/main/resources/web/app.js:91` (refresh button binds directly to `run`); `app/src/main/resources/web/app.js:78–82` (selected action executes, then form fields reset).
- Trigger: choose station/line deletion, select a record and delete it. Successful mutation calls `refresh(); fields()`, rebuilding the selector with the first surviving record selected. Click the result panel's **刷新** button. It calls the same mutation handler and asks only the generic deletion confirmation; confirming now deletes the newly selected surviving record, although the user requested a result refresh. For `lineRemove` the refresh can remove another membership without a confirmation at all. Other selected write actions are likewise submitted by this button.
- Impact: a control presented as a read refresh is an additional write entry point, with automatically changed target selection after successful writes. Disabling only the form submit button also leaves refresh available during an outstanding write.
- Fix: make refresh strictly read-only: refresh inventory/statistics and/or repeat a stored read query. Hide/disable it for write results or explicitly load the affected object's read view. Preserve the selected surviving target where appropriate. Apply the pending-request guard to every route into write submission.
- Verification needed: a browser or DOM-level regression test that selects a write action, clicks refresh before and after completion, and asserts zero mutation requests from refresh; cover station/line deletion and removal. Existing `WebTest` checks HTTP API guards but never executes frontend JavaScript, so it cannot catch this issue.

### I2 — Operating-only routing accepts a construction-only same-station journey

- Location: `app/src/main/java/metro/MetroService.java:78–88`; `app/src/main/java/metro/Router.java:26–29` and `:42–44` (endpoints accepted before any traversal).
- Trigger reproduced with the already-built application, without changing data:

  ```text
  java -Dfile.encoding=UTF-8 -jar app/build/metro.jar --action route start=230 end=230 planned=false
  ```

  It returns `found:true`, `planned:false`, zero stops and the Luohu 梨园 station (`station_id=230`). This station belongs only to the construction network. The source distinguishes it from operating Longgang 梨园 (`station_id=229`).
- Cause: service endpoint validation uses all physical station IDs; only the adjacency query filters `Operation`. A zero-edge journey never reaches that filtered graph. Shared construction-only landmark candidates can have the same problem.
- Impact: the UI's **仅运营网络** setting can report a successful journey at a station excluded from that network, contrary to the implementation plan's explicit planned-station guardrail.
- Fix: validate/filter endpoint candidate sets against eligible membership status within the same snapshot before invoking the router. For an operating query require at least one `Operation` membership. Do not use “has an adjacency edge” as the eligibility test, because a legitimate one-station operating line must still support a same-station journey. For landmark sets retain eligible candidates and report clearly if none remain. Keep planned-network behavior explicit.
- Verification needed: both routing modes for construction-only identical endpoints under `planned=false/true`, plus mixed-status/multiple landmark candidates and a single-station operating line.

## Minor findings

1. **Missing Content-Type becomes HTTP 500.** `app/src/main/java/metro/WebServer.java:54` calls `startsWith` on a nullable header. A valid-token POST without `Content-Type` reaches the generic internal-error handler instead of returning the intended 415. Read the header into a nullable variable and reject absent/unsupported values consistently. This does not bypass write authentication.
2. **Startup does not verify the complete required schema.** `app/src/main/java/metro/Main.java:44` calls only `stats`, which does not reference `line_station` or the Q7 function. A partial/manual schema installation can start successfully and fail later on fundamental operations. The approved technical route explicitly calls for a startup structure check; verify the six required tables/required function or a clear schema marker and report a useful repair instruction. Ordinary complete imports are unaffected.
3. **Batch insertion cannot represent heterogeneous membership attributes atomically.** `app/src/main/java/metro/MetroService.java:30–35`, the CLI menu and frontend provide a list of station IDs but one shared status/year/time tuple. This is openly disclosed by the interface, so it is not silent data corruption. However, the technical route asks for explicit attributes for every inserted station. A batch containing stations with different opening years/statuses cannot be represented as one atomic request. Consider an optional structured per-station format, or document this as a deliberate scope limitation and require separate operations when attributes differ.

## Inspection and evidence

Read the implementation plan, relevant data-model/CRUD/routing/interface requirements in `项目要求总结与技术实现路线.md`, and `docs/progress.md`. Inspected `tools/generate_import.py`, all non-generated SQL, import SQL transaction/cleanup boundaries, all `app/src/main/java/metro/*.java`, all web HTML/JS/CSS, all currently present build/run/test/local-db PowerShell scripts, `app/pom.xml`, and every Java test runner plus the Python importer tests. No `.codegraph` directory exists at either workspace or implementation root, so CodeGraph was not applicable.

Accepted the existing recorded green results rather than repeating them: Python 3 cases; RouterTest 6 scenarios; real PostgreSQL 12.1 Q1–Q7/CRUD/rollback/simultaneous insertion; HTTP homepage/API/method/token/origin guards; reported 439 stations, 29 lines, 567 memberships, 1304 exits and 3271 landmark links. The only additional execution was read-only lookup of the two 梨园 identities and the new same-station construction-only route counterexample above. No existing suite was rerun.

The locking review considered application-to-application writes: topology mutations consistently acquire one transaction advisory lock before line locks, making multi-line deletion and insertion serial. Station updates do not change station IDs/memberships. Deferred uniqueness handles intermediate station-position collisions, and failed transactions roll back. The schema does not independently enforce gap-free positions after arbitrary external SQL; the documented application protocol and import validation provide that invariant. This is an explicit boundary, not an additional finding.

## Declined judgments and limits

- Did not judge the correctness of the teacher-dependent Longgang 梨园 exit assignment, grouped-exit semantics or coordinate-column interpretation as real-world facts. They are explicitly configured/disclosed assumptions, and the importer rejects changed source hashes; teacher approval is outside code review.
- Did not claim the advanced fare feature is complete without approved data. The optional matrix loader and unavailable response preserve the stated evidence boundary; real fare accuracy requires an actual approved matrix.
- Did not rerun full import/integration/performance suites or validate measured speed/space claims. Those already have evidence or are still being prepared by the implementer; source review cannot establish performance numbers.
- Did not assess final README, packaging/performance documentation, release ZIP layout or a future `scripts/package.ps1`: these were explicitly still being authored during review. Windows build/run/local-db behavior was inspected statically, but a clean machine and Maven fallback were not exercised.
- Did not claim visual/accessibility or end-to-end browser QA from the existing HTTP smoke test. That runner does not execute JavaScript, submit UI forms, or validate route rendering; I1 particularly needs a frontend regression check.
- This artifact records findings against the inspected source. Subsequent fixes need targeted verification before marking these findings resolved.

## Implementer resolution after review

2026-10-24: I1 and I2 are fixed. I1 has Node DOM regression tests for stationDelete, lineDelete and lineRemove refresh, observed failing then passing. I2 has real PostgreSQL operating/planned same-station tests in both route modes, also observed failing then passing. The complete Python/Node/Java/integration/HTTP/CLI suite passes after fixes. See verification.md and progress.md for evidence and retained Minor limitations. This appended resolution preserves the reviewer's original assessment of the earlier source.

