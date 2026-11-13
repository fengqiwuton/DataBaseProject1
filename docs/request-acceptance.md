# request.txt 修改与验收

2026-11-12。以项目 PDF 和 Lecture 7 为依据，先自查修正 ER，再逐项验收。

- [x] **Task 1：软件制图与课程画法。** [概念图 PNG](ER_lecture7/概念ER图_Lecture7.png) 由 Python/Pillow 生成，并提供同版 [SVG](ER_lecture7/概念ER图_Lecture7.svg)。原图的一对多只有参与次数，现补上指向「一」端的箭头和 1:N；旧图以数据库代理编号把出口画成普通实体，现按业务身份画弱实体。实体主键用实线下划线，部分键用虚线下划线；概念图没有外键列。原来靠说明推断的 CSV 列改为直接标注，已逐字核对 12＋4 个原列名。
- [x] **Task 2：关系设计。** [报告配图与列说明](report-task1-task2.md) 含 DataGrip 从实库导出的六表图、三范式和键的说明。[schema.sql](../sql/schema.sql) 仅含六条 CREATE TABLE；在独立空库创建 schema 后实际建出了六表。
- [x] **Task 3.2：一键导入。** 新版 [import.sql](../sql/import.sql) 在 DataGrip 两次均完成 5/5 条顶层语句并提交，显示 825 ms、586 ms。六表共 5,620 行与源 CSV 映射逐字段一致，提速方法与对照结果见 [答辩指南](defense-guide.md)。
- [x] **Task 3.3：数据核验。** [queries.sql](../sql/queries.sql) 的七类题目和两组 Q7 例子均执行并核对；换参位置与参考输出见答辩指南。
- [x] **Task 4：按现场顺序演练。** 实际创建站/线，在新线路按给定顺序加入三个现有站，再插入和移出新站。站编号顺序 1、2、3 → 1、新站、2、3 → 1、2、3；Num 始终从 1 连续，新站仍存在。网页修改后直接显示同一条线路的 Num 表；[备用 SQL](../sql/defense-line.sql) 也已实跑。完整 Python、前端、Java、真实 PostgreSQL 和 HTTP 测试通过。

验证使用独立数据库 `metro_request_verify`，没有重建或改写原 `metro_test` 的数据。课程最终 PDF 和真实组员贡献由组员整理。
