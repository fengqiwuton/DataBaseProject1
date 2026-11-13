# 答辩操作：Task 3.2、3.3、4

把导入和写入操作都指向答辩专用库。演练用独立库 `metro_request_verify`；项目默认运行配置仍连接 `metro_test`。开始前请核对 DataGrip 的数据库名和应用的 JDBC URL 指向同一个答辩库。

## Task 3.2：一键导入

1. 在 DataGrip 文件树右击 [import.sql](../sql/import.sql)，选 **运行 'import.sql'**（英文界面 **Run 'import.sql'**）。首次配置时在「目标数据源/架构」添加答辩专用库，运行整个文件；文件内的 `BEGIN/COMMIT` 控制事务。
2. 执行完成后刷新 `project1`，核对 `district/station/metro_line/line_station/station_exit/exit_landmark` 行数依次为 **10 / 439 / 29 / 567 / 1304 / 3271**。重复执行会重建这六表并恢复初始数据，应在 CRUD 演示前完成。
3. 答辩时可说明，CSV 解码、去重、拆分和转义在生成脚本时完成。运行时每张表用一条多值 `INSERT`，由 PostgreSQL 在一个 `DO` 块里完成重建、导入、校验和统计，减少客户端逐条发命令的往返。三个辅助索引在数据写完后集中创建。全程保留主键、唯一约束和外键，任一步失败，整个事务回滚。

本机 DataGrip 2026.2.5 两次执行新版均完成 **5/5** 条顶层语句并提交，显示 **825 ms、586 ms**。同机 PostgreSQL 12.1 上另用同一个 JDBC 连接交错跑新旧脚本各 15 次，耗时中位数为 **765.8 → 750.1 ms**。两次 DataGrip 时间用于说明现场执行，版本提速用同条件的 JDBC 对照。详细口径见[导入性能与验证](verification.md)。

终端备选：`psql -X -h 127.0.0.1 -p 55437 -U metro -d <答辩库名> -v ON_ERROR_STOP=1 -f sql/import.sql`。

## Task 3.3：Q1–Q7

提前在 DataGrip 打开 [queries.sql](../sql/queries.sql)，使用右上角连接选择答辩库；按评委顺序选中对应 SQL 执行。Q4、Q5 修改线路英文名；Q6 修改 `LIKE` 前缀并保留尾部 `%`；Q7 修改站名、线路英文名和 n。题目示例在独立库实测：

| 查询 | 结果 |
|---|---|
| Q1 / Q2 | 439 站 / 29 线 |
| Q3 | Bao'an 58、Dapeng 1、Futian 52、Guangming 24、Longgang 70、Longhua 21、Luohu 32、Nanshan 67、Pingshan 16、Yantian 9 |
| Q4：Line 5 | 2011 年 27 站，2019 年 7 站，2025 年 3 站 |
| Q5：Line 1 | Chegongmiao、Shenzhen University 并列，各 10 个出口 |
| Q6：塘朗% | 6 条，涉及深大丽湖、塘朗、桃源村，按英文站名排序 |
| Q7：Mawan / Line 5 | n=5：NULL、Linhai；n=2：Liwan、Qianwan |

## Task 4：现场编排

启动 `./scripts/run.ps1 -Web`，浏览器打开 [本地界面](http://127.0.0.1:8088)。命令行可用同一启动脚本（去掉 `-Web`），用菜单 2、6、10、9、11 分别新增站、线、插入、查看站序、移出；CLI 字段 `position` 对应 `Num`。

| 顺序 | 界面操作 | 应核对什么 |
|---|---|---|
| 1 | 站点与出口 → 新增站点，填中英文名和行政区，坐标可空。 | 记下返回的站点编号，例：440。 |
| 2 | 线路编排 → 新增线路，例：演示线 / Demo Line。 | 记下线路编号；初始 0 站。后续编排操作会自动选中这条新线路，仍可手动切换。 |
| 3 | 指定位置插入站点 → 选择刚新增的线路，位置填 1，按评委顺序输入既有站点编号（英文逗号隔开）。 | 提交后直接出现该线路的 Num 表；例：原 A=1、B=2、C=3。 |
| 4 | 对同一条线再次插入，位置填 2，站点填步骤 1 的编号。 | A=1、新站=2、B=3、C=4；后续站点顺移。 |
| 5 | 移出线路 → 仍选刚新增的线路，选择新站后提交。 | 恢复 A=1、B=2、C=3；新站仍能在站点查询里找到。 |

备选核对：[defense-line.sql](../sql/defense-line.sql) 改一处线路英文名，随后每次操作后在 DataGrip 执行。查询通过 `position AS "Num"` 显示最新站序。网页与 CLI 均通过 JDBC 使用同一事务逻辑：插入时后续站序整体后移，移出时按顺序重新编号，任何失败不会留下半次更新。
