# Metro Project Implementation Plan

> For agentic workers: use superpowers:executing-plans, implementing tasks in order with test evidence in progress.md.

Goal: implement the approved six-table PostgreSQL metro system with self-contained SQL, Java CLI and local browser interface.

Architecture: a deterministic Python offline importer generates SQL and source mappings; Java 17 JDBC repository performs transactions; a shared service serves CLI and an optional local HTTP UI. Routing loads one consistent snapshot and performs BFS or lexicographic Dijkstra.

Tech Stack: PostgreSQL 12-compatible SQL, Java 17+, pgJDBC pinned to the official download version 42.7.14, Python standard library, JDK HttpServer.

Spec: ../项目要求总结与技术实现路线.md

## Global Constraints
- Preserve original CSV, 439 physical stations, 29 lines, 567 line memberships; expanded exits 1304 and links 3271 under disclosed mapping.
- Six 3NF tables; PK/NN/business unique; all involved in acyclic FK relationships.
- import.sql contains complete DDL and INSERTs, deterministic cleanup and one transaction; Q7 returns two rows including NULL.
- All mutations use parameter binding and transactions; line edits lock parent rows and defer position uniqueness.
- Fare is unavailable unless explicitly supplied; never fabricate fares, branch links or running times.
- Implement only in Project1_v0. Directory is not a Git repository, so worktree/commit steps do not apply; do not initialize or relocate the user's repository.

## Review Focus
1. Homonymous stations and ambiguous exit mapping must not merge identities.
2. Multi-exit groups and empty landmarks must preserve all source records.
3. Transaction failure and concurrent topology changes must preserve contiguous positions.
4. Extreme Q7 n, missing endpoints, planned stations and disconnected graphs must fail clearly.
5. Local web access must not expose unrestricted SQL or allow cross-origin mutation.

## Task 1 — importer and schema
Files: tools/generate_import.py, tests/test_importer.py, sql/{schema,functions,queries,import}.sql, generated/{audit,source_mapping}.json, config/data-rules.json.
Interfaces: load_model(archive, rules)->dict; build(output,archive,rules); SQL schema project1 and six table names from spec.
- [x] Write/run failing tests for 439 identity, grouped exits, missing landmarks, Q7 expected samples and deterministic generation.
- [x] Implement source validation, fixed assumptions and reproducible model; emit DDL/data/function/indexes/assertions/sequences.
- [x] Run Python suite; import twice into an isolated PostgreSQL test cluster and verify expected query results.

## Task 2 — repository and service
Files: app/src/main/java/metro/{Config,Db,MetroRepository,MetroService}.java; app/src/test/java/metro/IntegrationTest.java.
Interfaces: repository.query(sql,Object...)->List<Map<String,Object>>; service.execute(action,Map<String,String>)->Object; action allowlist used by both frontends.
- [x] Write/run failing integration assertions for stats, Q1–Q7, CRUD, station identity, bulk insert/remove, rollback and concurrency.
- [x] Implement shared parameterized repository/service; verify against actual test PostgreSQL.

## Task 3 — routing
Files: app/src/main/java/metro/Router.java; app/src/test/java/metro/RouterTest.java.
Interfaces: records Edge(from,to,line), Result(found,stations,lines,transfers,stops); route(edges,starts,ends,mode).
- [x] Write/run failing tests for shortest stops, minimum transfers with stop tie-break, multi-source, same station and disconnected graphs.
- [x] Implement snapshot graph loading and algorithms; run full suite.

## Task 4 — interfaces and launch
Files: app/src/main/java/metro/{Main,WebServer,Json}.java, app/src/main/resources/web/index.html, scripts/{build,run,test,local-db}.ps1, app/pom.xml, config/db.example.properties.
- [x] Add CLI input/output smoke and HTTP endpoint tests; observe missing implementation.
- [x] Implement all CLI operations and allowlisted local UI API; local-only binding, POST origin/token checks and escaped output.
- [x] Verify launch, browser response, station/line management, routes, Q7 and fare unavailability.

## Task 5 — delivery
Files: README.md, docs/{verification,ai-usage,er}.md, scripts/package.ps1.
- [x] Run full Python/Java/SQL/HTTP suite, record actual performance and two-run import evidence.
- [x] Fresh reviewer inspects source and evidence; fix important findings with regression tests.
- [x] Build runnable jar and source ZIP; clearly distinguish missing external fare data and final course screenshots/report.
