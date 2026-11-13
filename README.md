# 深圳地铁数据管理 · CS307 Project 1

依据本目录《项目要求总结与技术实现路线》实现。包含完整 PostgreSQL 导入、Java 命令行、本地浏览器界面、测试、源数据映射和实测记录。

## 快速开始（Windows）

需要 **JDK 17+**、PostgreSQL 服务端/客户端工具、Python 3.10+（仅重新生成 SQL 或跑 Python 测试时需要）。构建不依赖 Maven、npm 或额外 Python 包。已附 pgJDBC 42.7.14 驱动及校验值；缺失时构建脚本从官方来源下载。

在 PowerShell 中进入本目录：

```powershell
Set-Location D:/DB_project1/Project1_v0

# 首次初始化/启动本项目独立测试实例；默认端口55437，不连接已有数据库。
./scripts/local-db.ps1 -Action start

# 明确执行一次数据重建（同一专用测试库中可重复运行）。
./scripts/local-db.ps1 -Action import

# 编译并进入完整交互菜单。
./scripts/build.ps1
./scripts/run.ps1
```

如果 PostgreSQL 工具不在 PATH，给 local-db 脚本指定其 bin 目录：

```powershell
./scripts/local-db.ps1 -Action start -PgBin 'D:/labkey/apps/postgresql-12.6/bin'
./scripts/local-db.ps1 -Action import -PgBin 'D:/labkey/apps/postgresql-12.6/bin'
```

本地辅助实例只监听 127.0.0.1，以 trust 方式供本机演示；数据保存在 `.runtime/pgdata`，账户 metro，库 metro_test。它是测试配置，不能用于远程共享部署。文件夹名不代表服务版本；本机实际验证为 PostgreSQL **12.1**。维护中的 PostgreSQL 版本同样可按下面方式连接，本实现采用 12 兼容语法。

使用已有**专用作业库**时，复制 `config/db.example.properties` 为 `config/db.properties` 并填写连接；在 DataGrip 连接该库后执行 `sql/import.sql`。也可用环境变量覆盖：

```powershell
$env:METRO_DB_URL = 'jdbc:postgresql://127.0.0.1:5432/your_project_database'
$env:METRO_DB_USER = 'your_user'
$env:METRO_DB_PASSWORD = 'your_password'
./scripts/run.ps1
```

**import.sql 会在一个事务中重建所选数据库的 project1 schema 内六张表与 Q7 函数，清除这些表的已有修改。** 不要把它当作程序每次启动必跑的步骤。脚本不会清理其他 schema；启动程序也不会自动重建数据。`local-db.ps1 import` 还会核对服务的数据目录，避免误操作其他实例。

## 浏览器界面

```powershell
./scripts/run.ps1 -Web
```

浏览器打开 [本地界面](http://127.0.0.1:8088)。也可从命令行菜单第 26 项启动同一界面。界面包括站点/出口、线路编排、路线、Q1–Q7；两种入口共用 Service 和事务逻辑。服务仅绑定回环地址，修改操作使用 POST 与每次启动生成的令牌。

菜单与网页都使用 ID 明确目标；站点选择显示中文名、行政区和 ID。新增车站先用“行政区 ID 列表”查看行政区；批量插站用英文逗号输入 ID，其统一属性由用户填写，之后可逐站修改。修改车站是完整字段更新，空坐标表示清空；界面会填入该站当前字段。删除车站会删除出口、移除所有线路关系并修复各线站序；移出线路不删除车站。

网页资源和 API 已测试，截图视觉核验被运行环境的自动审批策略阻止，**尚无完成视觉验证的宣称**。

## 无交互运行与 DataGrip 核验

```powershell
java -jar app/build/metro.jar --action q1
java -jar app/build/metro.jar --action q4 'line_name=Line 5'
java -jar app/build/metro.jar --action q7 station_name=Mawan 'line_name=Line 5' n=5
java -jar app/build/metro.jar --action stations search=梨园
```

CLI 的输出/输入编码为 UTF-8，PowerShell 启动脚本会设置终端编码。`--action` 支持与界面共用的站点、线路和数据核验操作，字段名见 `MetroService.java` 和交互菜单。

网页的站点搜索可选择匹配站点编号、中文站名、英文站名、行政区或全部字段。编号支持 `347` 或 `#347`，精确匹配。名称和区名支持包含匹配。详情、路线和插站可输入站名或编号，也可从候选中选择。插站按列表顺序提交，多个站点可以用逗号分隔。

网页的 [SQL 查询](http://127.0.0.1:8088/sql) 每次执行一条只读语句，最多显示 200 行。用 `local-db.ps1 -Action import` 导入时会配置查询账号。已经导入数据的本地项目库可运行 `./scripts/local-db.ps1 -Action sql-reader` 单独配置，保留现有数据。使用自己的 PostgreSQL 实例时，可在目标库以表所有者执行 `sql/web-reader.sql`，或准备具有项目表 SELECT 权限的专用账号并设置 `METRO_SQL_USER`、`METRO_SQL_PASSWORD`。

DataGrip 中运行 `sql/queries.sql`，包含完整 Q1–Q7 默认示例。`sql/q1.sql`–`q7.sql` 则是 JDBC 绑定参数版本，`?` 需由应用绑定或在客户端输入参数。若要原样使用题目不带 schema 的函数调用，先运行：

```sql
SET search_path TO project1, public;
SELECT get_station_n_neighbor('Mawan','Line 5',5);
```

Q7 按较小站序、较大站序返回两行；越界保留 NULL，n=0 返回当前站两次，负数/空值/不存在或歧义目标报错。该 n=0 定义是已披露的本实现口径。

按新增 [request.txt](request.txt) 整理的入口：[逐项验收](docs/request-acceptance.md)、[Task 1–2 报告配图](docs/report-task1-task2.md)、[Task 3–4 答辩操作](docs/defense-guide.md)。单独提交的 `sql/schema.sql` 只有六条建表语句；独立执行前先创建 `project1` schema。网页在同一条线路插站或移站后立即显示 **Num（站序）**，备用核对 SQL 为 `sql/defense-line.sql`。

## 路径与票价边界

- `stops` 使用 BFS 求最少经过站数；`transfers` 使用 `(换乘数,站数)` 字典序 Dijkstra。
- 默认只沿相邻站序且两端均为 Operation 的边；可显式选择包含在建网络。未从 CSV 得到的分期连接不补造。
- 地标路线按完整地标名称匹配，多起点/多终点一次搜索，结果带出口候选；先用地标搜索找到完整名称。
- 不计算没有数据依据的运行时间。没有认可票价数据时明确返回 unavailable，不把站数估算冒充真实票价。

票价查询代码已提供可选的**有向票价矩阵**接口。教师认可并提供数据后，保存 UTF-8 CSV，表头严格如下，后续每行填写真实 origin_station_id、destination_station_id、非负两位小数金额：

```text
origin_station_id,destination_station_id,amount
```

将 `METRO_FARE_CSV` 设置为文件的绝对路径后启动程序；不会自动假设反向票价相同。ID 必须对应本次导入的数据。仓库不附虚构价格；**真实票价子项仍取决于外部认可数据**。

## 重新生成、测试与打包

```powershell
# 不连接数据库，只从内附原始压缩包生成SQL和审计映射。
python tools/generate_import.py

# 单元测试（不要求数据库在线）
./scripts/test.ps1

# 集成测试：仅针对初始导入状态的专用测试库运行，会创建/删除测试站线。
# 不要在个人修改过的作业数据或正式库上运行。
./scripts/test.ps1 -Integration

# 制作自包含源码/运行交付包，排除运行中的数据库、私密配置和临时文件。
./scripts/package.ps1

# 只读性能采样；不修改数据库，结果为generated/benchmark.json。
python tools/benchmark.py

# 停止本项目本地测试实例（保留数据文件）。
./scripts/local-db.ps1 -Action stop
```

若本机 PowerShell 执行策略禁止脚本，请按本机授权方式运行，不需要修改系统级策略。Maven 使用者可在 `app` 目录运行 `mvn package`，产物及驱动位于 `app/target`；本机没有 Maven，所以**只验证了不依赖 Maven 的构建路线**。Java 测试为独立 main 测试类，应通过 `scripts/test.ps1` 执行，不应把 Maven 的默认零测试结果误认为测试覆盖。

构建前先关闭正在运行的本程序，Windows会锁定运行中的JAR。Node如已安装，测试脚本还会运行前端刷新按钮的回归测试；它不是运行程序的依赖。

兼容 Windows PowerShell 5.1 与 PowerShell 7：`scripts/*.ps1` 统一保存为带 BOM 的 UTF-8。编辑这些脚本时请保留该编码；仅在脚本执行后设置终端编码，不能修复脚本读取阶段的解析乱码。测试已加入 Windows PowerShell 原生解析检查。

查看本地数据库可用 `./scripts/local-db.ps1 -Action connect`。看到操作提示后直接输入 `\dt project1.*` 或 SQL，不必等 `metro_test=#` 提示符；输入 `\q` 退出。该入口用英文表头、UTF-8 中文数据，避免旧版 Windows `psql` 直接输出时乱码；`import` 也使用英文状态提示。退出后恢复原终端编码，不影响其他项目或窗口。查看已有数据无需重新导入。

## 目录与实现状态

```text
app/src/main/java/metro/  数据库、事务、业务、路径、CLI、HTTP、票价和JSON
app/src/main/resources/  本地界面HTML/CSS/JS
app/src/test/java/metro/ 算法、真实数据库、HTTP、编码和票价测试
app/lib/                固定版本JDBC运行依赖
app/build/metro.jar     已构建的入口JAR（需同时保留app/lib）
sql/                    独立DDL、完整导入SQL、函数与查询
tools/generate_import.py 只用标准库的确定性生成器
source-data/Archive.zip 原始输入的逐字节副本
config/data-rules.json  明确的数据假设和源文件哈希
generated/              审计、逐行映射及性能实测JSON
scripts/                构建、启动、本地库、测试和打包
docs/                   实施计划、验证记录、ER说明、AI使用和代码审查
```

核心计数：10 区、439 站、29 线、567 条线路站点关系、1304 出口、3271 出口地标关联。六表满足本设计的 3NF、主键/业务唯一性与无环外键约束。详细口径见原方案及 `config/data-rules.json`；梨园出口归属、组合出口展开和坐标映射仍应由组员向教师确认。

已提供课程概念 E-R 图、DataGrip 实库关系图、报告配图说明、AI 使用说明和验证记录。课程最终 PDF、真实组员分工由组员完成；真实票价需要教师认可的数据。最终提交截止时间以课程 PDF 为准。
