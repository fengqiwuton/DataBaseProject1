# 实现与验证记录

## 2026-11-13：Task 3.2 导入优化

旧版每批最多 500 行，产生 15 条 INSERT 和 48 条顶层语句。新版每表一条多值 INSERT，合并序列同步和 ANALYZE，把重建、装载、索引和行数校验交给一个 PostgreSQL `DO` 块。客户端执行 5 条顶层语句，内部仍含六条建表语句和全部 INSERT。保留主键、唯一约束、外键、事务和提交时的同步写入。批量事务、装载后创建辅助索引及更新统计的依据见 [PostgreSQL 批量装载文档](https://www.postgresql.org/docs/12/populate.html)。

| 指标 | 旧版 | 新版 |
|---|---:|---:|
| 数据 INSERT 数 | 15 | 6 |
| 客户端执行的顶层语句数 | 48 | 5 |
| 同连接 JDBC 导入中位数 | 765.8 ms | 750.1 ms |

计时环境为同一台 Windows 机器、同一独立 PostgreSQL 12.1 验证库、pgJDBC 42.7.14。预热后交错执行两个版本各 15 次，从发送第一条语句计时到 COMMIT 返回，包含客户端往返，不含连接建立及 DataGrip 界面操作。中位数下降约 2%，单次耗时波动大于该差值。DataGrip 2026.2.5 另两次运行新版，分别显示 825 ms 和 586 ms，均为 5/5 条完成。这两次用于确认客户端兼容性。

新版在默认 GBK 的旧版 Windows psql 下连续导入两次成功。六表共 5,620 行逐字段匹配 CSV 映射，Q1–Q7 输出与旧版一致。另核对了 4 个自增序列、5 个已验证外键和表统计信息。将测试副本中的预期行数故意改错后，已存在的表及数据均保留，确认事务回滚。5 项 Python 测试通过，计时和故障注入使用独立验证库。

## 2026-11-12：按 request.txt 验收

- 核对课件第 31、35、45–46 页；新版概念 E-R 图覆盖两份 CSV 的 16 个原列名。DataGrip 2026.2.5 从独立验证库实际导出 1936×848 的六表关系图。
- 纯 DDL 在独立空库实际创建六表。DataGrip 执行最终 import.sql 两次均完成 48/48 条语句，耗时 1.203 秒、0.953 秒并提交。六表逐字段匹配 CSV 映射后的 5,620 行；Q1–Q7 实际输出逐行核对一致。
- 完整测试在 Windows PowerShell 5.1 指向独立库运行：5 项 Python、4 项 Node 回归及 Java、真实数据库、HTTP、CLI 全通过。另通过入口 JAR 实演新站新线与站序 1、2、3 → 1、新站、2、3 → 1、2、3，且移出后仍可查询新站；备用 SQL 返回了实际 Num。
- [逐项验收](request-acceptance.md) 包含产物入口。验证期间没有重建或修改原 `metro_test` 的数据。

## 终端表头、中文查询结果与导入提示显示

用旧版 Windows psql 12.1、`LANGUAGE=zh_CN` 与 `PGCLIENTENCODING=GBK` 复现表头及行数乱码；只切换数据库连接编码时，中文提示与结果仍可能混用两种编码。`local-db.ps1` 的 psql 调用现临时使用 C 语言环境和 UTF-8；`connect` 由 PowerShell 解码查询输出，避开旧客户端直接写终端的转换问题。Windows PowerShell 5.1 实测显示六张表、中文查询词与结果“梨园”、以及“卓越•INTOWN购物中心”。独立实例的完整 `-Action import` 输出 `(1 row)` 和 `COMMIT`，站点数439；没有重新导入原 `metro_test`。

## 2026-11-09：GBK 客户端导入兼容修复

用`PGCLIENTENCODING=GBK`在独立临时数据库复现了UTF-8导入文件在第1622行报`0xa1 0x98`转换错误，失败事务没有留下表。导入生成器现于BEGIN后、首个中文数据之前设置事务内UTF-8，生成的import.sql仅增加该设置，数据和DDL未改变。同一GBK客户端连续两次执行新脚本均COMMIT，事务结束时客户端编码恢复GBK；用UTF-8查询逐值核对六表（10、439、29、567、1304、3271行），均与源数据模型一致。Python全套5项通过。未重建现有metro_test数据库。

## Windows PowerShell 兼容修复（用户反馈后）

此前脚本没有UTF-8 BOM，Windows PowerShell 5.1会按系统本地编码读取中文源文件，造成字符串终止符/花括号解析错误。已在该宿主中复现五份脚本解析失败；统一补充UTF-8 BOM后，两项专项回归通过。随后直接以Windows PowerShell运行完整test.ps1：5项Python测试、3项Node回归及全部Java/真实数据库/HTTP/CLI测试通过。从C:/Users/Lenovo目录用Windows PowerShell运行run.ps1 -Web -Port 18089，成功启动，实际HTTP统计返回439站、29线。不是仅在PowerShell 7中复测。所有脚本和交付ZIP已同步更新。

验证日期：2026-10-24。Windows、JDK20.0.2（编译目标Java17）、PostgreSQL12.1、pgJDBC42.7.14。测试使用本项目`.runtime/pgdata`、127.0.0.1:55437、metro_test专用库，没有连接或重建用户已有数据库。

## 已验证

- CSV生成器：3项Python测试通过，覆盖身份/计数、保守出口解析、空地标保留、源行映射、两次生成字节一致、独立INSERT及引号转义。
- 完整import.sql在同一测试库执行两次成功，均COMMIT；queries.sql全部默认示例成功。439站、29线、567条关系、1304出口、3271出口地标关联。
- RouterTest：6个场景通过，包含最少站、最少换乘、换乘平局取最少站、多源、同站、不可达和非法模式。
- IntegrationTest：Q1–Q7、重名站、Q7越界NULL/最大整数/负数/零、站点增改删、线路增删、首中位置批量插站、回滚、移站压缩、并发两会话插站、物理站删除后重排、真实邻接路线、票价缺失边界通过。清理测试数据后回到439站。
- 运营/规划回归：两种路径模式均拒绝在仅运营网络查询Construction-only的梨园作为同站起终点；包含在建模式允许。
- WebTest：主页、统计API、GET禁止修改、缺令牌/跨来源POST禁止修改、JSON转义通过。
- 前端Node测试：站点删除、线路删除、移出线路三种状态下，重复刷新均只读。
- CliTest：强制GBK默认编码的子进程仍输出有效UTF-8中文；入口JAR的帮助、Q1和交互菜单输入0退出通过。
- 最终完整命令：`./scripts/test.ps1 -Integration`，所有实际运行套件通过；临时日志`.runtime/final-tests.log`不打包。

## 独立审查与修复

原始记录见code-review.md。两项Important问题均先以失败测试复现，再修复并全套验证：刷新重放修改已改为独立只读入口；在建同站误入运营查询已改为同一快照中按Operation关系过滤端点。Node三场景和真实数据库双模式回归均失败→通过。

三项轻微待完善项：有效令牌但缺Content-Type的手工POST返回500而非415；启动检查尚不覆盖每个函数/关系；批量插站使用统一属性，不支持单次请求中每站不同的年份/状态。常规网页请求带正确Content-Type，完整导入不受第二项影响；异质属性可随后逐站修改，但这些修改不是一个整体原子请求。

## 性能与空间

原始结果见generated/benchmark.json。复现：`python tools/benchmark.py --psql <psql路径>`。

六表pg_total_relation_size合计 **1,204,224字节，约1.15MiB**。包含表、索引、TOAST等，不是整个数据库目录占用；不含WAL、共享系统目录及独立序列，CRUD后的空闲页也可能包含在内。

每种查询在同一连接内先执行一次，再采样30次。下表为服务器带EXPLAIN插桩的预热执行时间，不含客户端、网络及界面。应用每次操作建立新连接，Q7可能承担首次函数规划成本，不能将预热值当作用户端响应时间。

| 查询及参数 | 中位数/ms | P95/ms |
|---|---:|---:|
| Q3 各区运营站 | 0.5365 | 0.876 |
| Q4 Line 5 | 0.1225 | 0.201 |
| Q5 Line 1 | 0.352 | 0.446 |
| Q6 塘朗% | 0.074 | 0.132 |
| Q7 Mawan / Line 5 / 5 | 0.253 | 1.459 |

这是单一方案的本机样本，没有做不同模式A/B比较，不宣称提升倍数或全局最优。设计通过消除站点/线路重复文本、复用唯一索引、少量反查/前缀索引、按需构图控制时间和空间。

## 未验证或依赖外部条件

- 自动审批审查拒绝启动无界面Edge浏览器截图，理由为策略阻止。未绕过，未完成视觉截图或真实浏览器端到端验证；HTTP和DOM测试不等同视觉验收。
- 本机无Maven，未验证Maven构建；无Maven脚本与JAR已验证。
- 未提供认可票价数据。FareTest使用临时合成测试数据，不作为真实票价交付。
- 梨园出口归属、出口展开、坐标列映射及n=0口径已披露，未替组员取得教师确认。
- 概念 E-R 图和实库 DataGrip 导出图已放入报告配图材料；最终课程 PDF 和真实组员分工仍由组员完成。

## 交付包核验

源码与运行文件共57项，ZIP完整性通过；排除了.runtime、db.properties和Python缓存。在带空格的新临时路径中解压后，JAR帮助、真实数据库Q1及全部Python测试通过。默认启动仍需要对应JDK和数据库环境，不把同机解压核验等同全新机器验收。

## 2026-11-13：一键导入结构优化与准确性复测

环境：Windows，PostgreSQL 18.6（x86_64-windows，msvc-19.44），本项目专用实例 `.runtime/pgdata`，127.0.0.1:55437，库metro_test，psql 18.6。此前记录只覆盖PostgreSQL 12.1；本轮同时确认同一份import.sql在18.6上完整导入成功。

### 改了什么

生成器 `tools/generate_import.py` 按"一个关注点一条语句"重写输出，数据、约束、断言与索引集合均未改变：

| 项 | 改动前 | 改动后 |
|---|---:|---:|
| 语句总数 | 49 | 27 |
| CREATE SCHEMA | 2（重复，其中一次是NOTICE来源） | 1 |
| DROP TABLE | 6 | 1（一条语句列六表） |
| INSERT | 15（每批500行） | 7（每批2000行） |
| ANALYZE | 6 | 1 |
| setval | 4条语句 | 1条语句4列 |

`sql/schema.sql`、`sql/indexes.sql`、`sql/functions.sql` 仍是生成器的唯一来源；`sql/schema.sql` 保持可独立执行，嵌入import.sql时由生成器剥离其首行建schema语句，避免重复。两次生成的import.sql字节一致，`generated/audit.json`与`source_mapping.json`未变化。

### 耗时（11轮交错采样，墙钟含psql启动）

| 变体 | 语句数 | 服务端语句合计中位（范围） | 墙钟中位 |
|---|---:|---:|---:|
| 优化前 | 49 | 129.4 ms（125.2–165.4） | 193.7 ms |
| 优化后 | 27 | 127.3 ms（122.5–130.6） | 165.7 ms |

墙钟下降约28 ms，与减少22次语句往返的量级一致；服务端计算本身只差约2 ms。**因此只报告实测值，不宣称加速倍数。** 单条语句拆解（优化后一次采样）：CREATE TABLE六表30–58 ms、COMMIT约20 ms、六表数据INSERT约45 ms、附加索引约7 ms、ANALYZE约5 ms、断言约3 ms；瓶颈是建表/目录与提交，不是数据装载，故不再进一步优化。

### 对照实验（同一实例）

| 变体 | 中位墙钟 | 结论 |
|---|---:|---|
| 逐行INSERT（5620条语句） | 796 ms | 比批量慢3–4倍，是批量插入的真实收益 |
| 先把索引建在空表上再装载 | 189 ms | 比后建索引慢约10%，验证当前顺序正确 |
| COPY FROM stdin 替代INSERT | 153 ms | 与批量INSERT差异落在噪声内，不因此违背"import.sql含全部INSERT"的要求 |
| SET LOCAL synchronous_commit=off | 126.9 ms | 与默认128.4 ms无差异，不引入降低持久性的改动 |

### 准确性（`python tools/verify_import.py`，44/44项通过）

- 两次连续导入内容md5一致（`ca4b7549ec2ab3edb67fa9ef8b47e89e`），确认可重复执行。
- 六表共5,620行**逐值对账**：每行每列与由CSV重新生成的模型完全相同（NULL按`\N`、time(0)按`HH:MM:SS`规范化后比较），不只是行数相同。
- Q1–Q7与`数据核验摘要.json`的预期一致（350个运营站分区、Line 5三年份、Line 1并列10个出口、塘朗%六行、Q7的NULL/Linhai）；Q7另验n=0、负数、NULL、不存在站、不在该线路、极大n。
- 四个identity序列的last_value等于各表max(id)；八项约束负例（重复站身份、空白名、重复出口码、非法状态、重复站序、孤儿地标、空白地标、越界坐标）全部被拒绝且失败后数据不变。
- 导入不触碰其他schema：预先建立的`other_work`在导入后仍存在；导入后project1恰为六表加一个Q7函数。
- 限制：`test_reproducible_standalone_sql` 在本机沙箱内因临时目录清理权限报错（断言本身为通过，两次生成字节一致已手工复核）；这是运行环境限制，不是生成器缺陷。

## 2026-11-13：draw.io 概念图与 Task 2 目录检验

### 概念图（Task 1 交付物）

- 同目录文件：`docs/ER_lecture7/概念ER图_drawio.drawio`（draw.io / diagrams.net 原生可编辑源文件）、`E-R_project1.png`（draw.io viewer 导出）、`概念ER图_drawio说明.md`（图例、口径、导出步骤）。生成脚本 `tools/draw_er_drawio.py`。
- 形式按 **Lecture 7 第 5 页**：实体为浅蓝表头 + 框内斜体属性列表（主键下划线）、联系为浅青菱形内斜体小写名、**箭头=至多一个**、**双线=全参与**、虚线矩形=联系属性、花括号=多值属性；不使用 `l..h`，图内无标题、无图例、无注释。
- **所有连线横平竖直**：连接点统一由 `connection_points()` 生成并对齐到同一 y 或同一 x，双线为两条平行水平线/垂直线；图中斜边只来自菱形本身。三项实现细节保证它成立：① 脚本内 `check_orthogonal()` 断言，布局若产生斜线直接抛错；② 连线样式加 `exitPerimeter=0;entryPerimeter=0;`，让 draw.io 按给定点直连、不再把端点二次投影到菱形周长；③ 几何坐标保留小数（菱形中心落在 .5 px），否则取整会把菱形整体移开 0.5 px。改完后独立从 XML 反算 9 条连线端点：5 条水平、4 条垂直，**最大偏差 0.000000 px**。（此前 `station`—`line_station` 一条连线曾因两端 y 不同而倾斜。）
- 结构校验：41 个单元（30 个顶点 + 9 条边），无悬空连接、无重复 id；2 条箭头边、1 条虚线边；XML 可解析；页面 1302×642。
- PNG 由 **diagrams.net 自身的 viewer** 渲染：headless Edge 打开 viewer（图数据经 deflate+base64 放在 URL 片段），截图后按非白像素裁边；离线时退回内置 Pillow 渲染器（同一坐标模型）。这样交付图片与网站上看到的一致，而不是"另画一张像的"。
- 双线实现为两条平行连线且终点取**菱形边界的精确交点**：此前用分数偏移时 draw.io 会把端点投影回菱形顶点，两条线收拢成"V"形；改为按菱形四条边求交后复测为平行。
- 更早的 `概念ER图_Lecture7.png/.svg` 用 `l..h` 标注，语义相同，保留作历史版本。
- 出口按**弱实体**画：双矩形（实体外侧再套一圈无填充矩形）、`exit_code` 虚线部分键、`exit_station` 双菱形识别联系，出口侧双线全参与；`exit_id` 是数据库代理键，概念层不画（与"外键不画进 ER 图"同层）。draw.io 的 `double=1` 对菱形有效、对矩形无效，所以矩形用外套框实现，双菱形用 `double=1`；部分键的虚线下划线用 HTML 行内 `border-bottom:1px dashed`，两处都由 draw.io viewer 渲染确认。

## 2026-11-13：Task 1 / Task 2 交叉核对（`tools/check_design.py`）

一次运行检查 71 项：**69 项通过、0 失败、0 警告、2 项交付物缺失**。核对范围是"图 ↔ DDL ↔ 活库系统目录 ↔ 文档"是否互相一致，而不只是各自存在。命令：`python tools/check_design.py --psql <psql路径>`（加 `--skip-db` 可只查图、DDL 与文档）。

**Task 1（概念 E-R 图，20%）**

- 图源与图片存在；XML 可解析、单页、9 条连线均绑定到有效图形，无悬空连接。
- 4 个实体（district、station、line、exit）逐个核对属性与主键下划线；3 个菱形（station_district、line_station、exit_station）；关系属性框恰含 `position/status/opening_year/first_train/last_train`。
- 基数：2 条箭头（"至多一个"）分别指向 district 与 station；2 组双线（全参与）位于 station 侧与 exit 侧；1 条虚线连接关系属性框。
- 连线全部横平竖直（复算最大偏差 0.0000 px）；图内除实体名、属性名、联系名外**没有任何文字**（无注释、图例、标题）。
- 图的属性集与 DDL 列逐表一致；外键列按概念建模惯例不画成实体属性（`station.district_id`、`station_exit.station_id` 由联系表达）。
- 绘图工具已注明：diagrams.net（draw.io），源文件 `.drawio`。

**Task 2（数据库设计，20%）**

- `sql/schema.sql` 独立可执行：只含 `CREATE SCHEMA` 与六条 `CREATE TABLE`，无 `INSERT/COPY/UPDATE/DELETE`、无 psql 元命令，共 23 列。
- `import.sql` 内嵌的就是这份 DDL（字符串级比对，不存在两份结构漂移）。
- 活库核对：6 张表；每表有主键；每表有非自增 ID 的 NOT NULL 业务列；业务 UNIQUE 齐全（`exit_landmark` 用复合主键）；5 条外键覆盖全部 6 表且方向无环；6 类 CHECK 齐全；4 个 identity 序列；无 `char(n)`、首末班为 `time(0)`、`opening_year` 为 `smallint`。
- 每条外键在图中都有对应联系：`station→district` 对应 `station_district`，`station_exit→station` 对应 `exit_station`，`line_station` 的两条外键对应 `line_station` 菱形；`exit_landmark→station_exit` 以多值属性 `{landmark_name}` 表达。
- 字段字典覆盖全部 23 列；1NF（原子值）、2NF（联系属性依赖完整键）、3NF（不存在传递依赖）在设计中均可追溯。

**仍未完成的 2 项（脚本不能替代）**

1. **DataGrip 实库关系图截图**——Task 2 明确要求由数据库客户端生成；本目录的 `六表关系映射图` 是人工绘制图，不能冒充。
2. **报告中的逐表逐字段解释正文**——素材（字段字典、DDL、设计说明）齐备，但尚未排成报告段落。

**报告里必须写清的三点**（最容易被追问）：概念名 `line`/`exit` 对应表 `metro_line`/`station_exit`；外键不画成实体属性、由联系表达；`exit_landmark` 由多值属性落为独立表。

### Task 2 表结构检验（35/35 项通过）

- `sql/schema.sql` 在全新数据库 `task2_check` 上**单独执行成功**：文件只含 `CREATE SCHEMA` 与六条 `CREATE TABLE`，无 `INSERT`/`COPY`/`UPDATE`/`DELETE`，建出 6 张表。
- 每表都有主键；每表都有**非自增 ID 的 NOT NULL 业务列**；除 `exit_landmark`（复合主键本身就是业务键）外每表都有业务 UNIQUE；5 条外键覆盖全部 6 张表且方向**无环**。
- CHECK 齐全：`status` 限定 Operation/Construction、`position > 0`、`opening_year` 1900–2200、名称/地标非空白、坐标范围、坐标成对为空。
- 类型适当：`integer` 代理键、`smallint` 年份、`time(0)` 首末班、`text` 名称；无 `char(n)` 补空格、无限长 `varchar`。
- 四个 identity 序列存在；`import.sql` 与 `schema.sql` 的约束集合**完全一致**（同名、同类型、同定义），说明独立 DDL 不是过期副本。
- `task2_check` 表结构快照（列数 / 主键 / 唯一 / 外键 / CHECK）：district 2/1/1/0/1，exit_landmark 2/1/0/1/1，line_station 7/1/1/2/3，metro_line 3/1/2/0/2，station 6/1/1/1/5，station_exit 3/1/1/1/1。
- **仍未完成、不能由本检验替代的部分**：Task 2 要求的"数据库客户端生成的关系图截图"（DataGrip 实库 Show Visualization），以及逐表逐字段解释的正文排版；`六表关系映射图` 是人工绘制图，不能冒充 DataGrip 截图。
