# 深圳地铁数据库从零构建与维护指南

## 1. 在 Windows 上从零启动

安装 Git、**JDK 17 或更新版本**以及 PostgreSQL 服务端和客户端工具。将 JDK 的 `bin` 加入 PATH。下列示例使用 PowerShell，PostgreSQL 路径请换成本机安装目录。Java 构建由 `javac` 和 `jar` 完成。Python 3.10+ 用于生成导入 SQL、测试和打包，Node.js 用于补充前端测试。 [JDK 安装说明](https://adoptium.net/installation/) · [PostgreSQL Windows 安装](https://www.postgresql.org/download/windows/)

```powershell
git clone https://github.com/fengqiwuton/DataBaseProject1.git
Set-Location DataBaseProject1
java -version
javac -version
$pgBin = 'C:\Program Files\PostgreSQL\18\bin'
& "$pgBin\psql.exe" --version

.\scripts\local-db.ps1 -Action start -PgBin $pgBin
.\scripts\local-db.ps1 -Action import -PgBin $pgBin
.\scripts\build.ps1
java -jar app/build/metro.jar --action q1
java -jar app/build/metro.jar --action q2
.\scripts\run.ps1
```

基线的 Q1、Q2 分别返回 439 站、29 线。CLI 输入 `0` 退出。在另一个 PowerShell 窗口打开同一目录，运行 `./scripts/run.ps1 -Web` 后访问 `http://127.0.0.1:8088/`，用 Ctrl+C 停止服务。Web 端口可通过 `-Port` 修改。Java 或前端源码更新后，先退出旧进程，再用 `./scripts/run.ps1 -Rebuild`（或加 `-Web`）启动。

`start` 在 `.runtime/pgdata` 初始化本地 PostgreSQL，默认端口 `55437`，库名 `metro_test`，用户 `metro`，密码留空。每次使用只需要启动实例和应用。`import` 用于初始化、切换数据版本或恢复基线。`build` 首次从 pgJDBC 下载固定版本驱动并校验 SHA-256，编译后的 JAR 引用 `app/lib`。若 Windows 拦截刚下载的可信脚本，可对该文件使用 `Unblock-File`。保存 `.ps1` 时保留带 BOM 的 UTF-8，以兼容 Windows PowerShell 5.1。

### 数据库连接与命令

| 本地脚本 `-Action` | 用途 |
|---|---|
| `start`、`status`、`stop` | 初始化或启动、检查、停止项目实例。停止后数据仍保存在磁盘。 |
| `import` | 重建 `metro_test` 中项目的六张表和 Q7 函数、载入数据、配置网页只读用户。 |
| `connect` | 进入 `psql`。输入 `\dt project1.*` 看表、`\d project1.station` 看结构、`\q` 退出。 |
| `sql-reader` | 为已导入的 `metro_test` 配置网页只读账号，保留现有行。 |

同一实例始终使用相同的 `-Port`。若示例改用 `55438`，相应设置 `$env:METRO_DB_URL = 'jdbc:postgresql://127.0.0.1:55438/metro_test'`。DataGrip 使用同一主机、端口、库名和用户名，展开 `project1`。本地项目实例只监听回环地址并使用 `trust` 认证。

使用现有 PostgreSQL 时，先建一个专用数据库，以其所有者运行 `sql/import.sql`。把 `config/db.example.properties` 复制为 `config/db.properties` 并填入 JDBC 地址、用户名和密码。`METRO_DB_URL`、`METRO_DB_USER`、`METRO_DB_PASSWORD` 优先于该文件，默认地址为 `jdbc:postgresql://127.0.0.1:55437/metro_test`。`METRO_CONFIG` 可指定另一配置文件。网页登录 SQL 查询还需要独立低权限账号，详见接口章节。

## 2. CLI、Web API 和 SQL 接口

交互式 CLI 使用 `./scripts/run.ps1`，无交互模式使用 `java -jar app/build/metro.jar --action 操作名 key=value ...`。包含空格的整个参数用引号括起。例如 `--action q7 station_name=Mawan 'line_name=Line 5' n=5`。读写动作与网页共用 Java 业务逻辑。交互式删除会提示输入 `DELETE`，无交互写入按给定参数直接执行。

网页入口为 `GET /`，SQL 工作区为 `GET /sql`。业务接口为 `GET /api?action=...` 或 `POST /api`。成功时返回 `{"data":...}`，失败时返回 `{"error":"..."}` 及相应 HTTP 状态。写入和 `sqlQuery` 必须用 POST，表单编码为 `application/x-www-form-urlencoded`。从首页 `meta[name=metro-token]` 读取当次启动令牌，放入 `X-Metro-Token`。请求仅限本机监听地址，若传 `Origin` 须与本地服务相符。

```powershell
$base = 'http://127.0.0.1:8088'
Invoke-RestMethod "$base/api?action=q4&line_name=Line%205"
$page = (Invoke-WebRequest -UseBasicParsing "$base/").Content
$token = [regex]::Match($page, '<meta name="metro-token" content="([^"]+)"').Groups[1].Value
Invoke-RestMethod "$base/api" -Method Post `
  -Headers @{'X-Metro-Token' = $token} `
  -ContentType 'application/x-www-form-urlencoded' `
  -Body @{action='sqlQuery'; sql='SELECT count(*) FROM project1.station'}
```

下表中的 `?` 表示可选字段。CLI 使用菜单或 `--action` 调用相应动作，HTTP 按表中方法调用。站点、线路、行政区 ID 均为正整数。网页的站名候选框会先解析出站点 ID，再提交给使用 ID 的动作。

| CLI 菜单 | `action` | HTTP | 参数与返回 |
|---:|---|---|---|
| `--action` | `stats` | GET | 无参数。返回站、线、出口、地标关联数量及数据库版本。 |
| 1 | `stations` | GET | `search?`、`match?`、`station_id?`。空搜索列出全部。`match` 可填 `all`、`station_id`、`name_zh`、`name_en`、`district`。搜索编号时支持 `#419` 或 `419`。显式 `station_id` 优先。 |
| 2 | `stationAdd` | POST | `name_zh`、`name_en`、`district_id`、`lon_mdeg?`、`lat_mdeg?`。返回新车站的 `station_id`。 |
| 3 | `stationUpdate` | POST | `station_id` 加新增车站的全部字段。坐标以千分之一度成对提交，均留空会清空。 |
| 4 | `stationDelete` | POST | `station_id`。删除物理站及出口，并修补受影响线路的站序。 |
| 5 | `lines` | GET | 无参数。列出线路和各线路站点数。 |
| 6 | `lineAdd` | POST | `name_zh`、`name_en`。返回新线路及编号。 |
| 7 | `lineUpdate` | POST | `line_id`、`name_zh`、`name_en`。 |
| 8 | `lineDelete` | POST | `line_id`。删除线路及其站线关系，物理车站继续保留。 |
| 9 | `lineStations` | GET | `line_id`。按 `position`（Num）返回站序。 |
| 10 | `lineInsert` | POST | `line_id`、`position`、`station_ids`（英文逗号分隔）、`status`、`opening_year`、`first_train?`、`last_train?`。从指定位置依次插入。 |
| 11 | `lineRemove` | POST | `line_id`、`station_id`。移出后续站序重新连续编号。 |
| 12 | `membershipUpdate` | POST | `line_id`、`station_id`、`status`、`opening_year`、`first_train?`、`last_train?`。更新站线属性。 |
| 13 | `q7` | GET | `station_name`、`line_name` 用英文名，`n` 为非负整数。按前后顺序返回两行，越界是 `null`，`n=0` 两行均为本站。 |
| 14 | `route` | GET | `start`、`end` 使用数字站点 ID，`mode?` 为 `stops`（默认）或 `transfers`，`planned?` 为 `true` 或 `false`（默认）。返回站序、经过线路及换乘次数。 |
| 15 | `landmarks` | GET | `search?`，按包含匹配返回最多 100 条地标和出口候选。 |
| 16 | `landmarkRoute` | GET | `start_landmark`、`end_landmark` 用候选中的完整名称，`mode?`、`planned?` 同 `route`。有线路时同时返回出口候选。 |
| 17 | `fare` | GET | `start`、`end` 支持完整中英文站名、正整数 ID 或 `#ID`，同名时按提示使用 ID。返回 `available`、金额和币种，或缺失原因。 |
| 18 | `stationDetail` | GET | `station_id`。返回车站、站线关系、出口和地标。 |
| 19 | `q1` | GET | 无参数。物理车站数。 |
| 20 | `q2` | GET | 无参数。完整线路数。 |
| 21 | `q3` | GET | 无参数。各区运营站数，换乘物理站计一次。 |
| 22 | `q4` | GET | `line_name` 用英文名。按开通年计数。 |
| 23 | `q5` | GET | `line_name` 用英文名。返回所有并列出口最多的站。 |
| 24 | `q6` | GET | `prefix` 为 SQL `LIKE` 模式，例如 `'prefix=塘朗%'`。 |
| 25 | `districts` | GET | 无参数。列出行政区及编号。 |
| 26、0 | 启动 Web、退出 |  | 交互式导航。Web 也可用 `--web [端口]` 单独启动。 |
| 网页 `/sql` | `sqlQuery` | POST | `sql`，每次一条只读查询。返回 `columns`、`rows`、`truncated`、`clipped`。最多显示 200 行。 |

站线状态取 `Operation` 或 `Construction`，开通年份范围 1900–2200，时刻用 `HH:mm`（可带秒）。`position` 从 1 起。`transfers` 按换乘次数优先，同次换乘取最少站数。`planned=true` 纳入在建线路。CLI 的完整字段提示见 [Main.java](../app/src/main/java/metro/Main.java)，参数与数据库操作见 [MetroService.java](../app/src/main/java/metro/MetroService.java) 和 [MetroRepository.java](../app/src/main/java/metro/MetroRepository.java)。

**数据库接口。** DataGrip 或 `psql` 直接执行 [`sql/queries.sql`](../sql/queries.sql)。`sql/q1.sql` 到 `sql/q7.sql` 是应用加载的 JDBC 模板，其中的 `?` 由应用绑定。`project1.get_station_n_neighbor(text,text,integer)` 可直接用 SQL 调用。`sql/defense-line.sql` 用于核对线路 `Num`。网页 `/sql` 使用 `METRO_SQL_USER`、`METRO_SQL_PASSWORD` 配置的角色，默认 `metro_sql_reader`。在自建实例上可由有建角色权限的管理员创建低权限角色，再由项目表所有者授权，可参考 [`sql/web-reader.sql`](../sql/web-reader.sql)。

## 3. 源 CSV 修改后如何更新

两份基线数据在 `source-data/Archive.zip`。`shenzhen_stations.csv` 每行表示一个站在线路上的一次出现，`station_exits.csv` 存放出口和地标。`config/data-rules.json` 保存源文件哈希、目标行数、重名站出口映射及坐标列解释。`tools/generate_import.py` 实现去重、组合出口拆分、编号和 SQL 转义。

1. 将两个 CSV 解压到项目外的工作目录，用 UTF-8 保存修改。保留原表头和 ZIP 内根层文件名。改同一物理站的名称、行政区或坐标时，核对其全部线路记录和对应出口。变更线路成员后保持 `Num` 从 1 连续，检查重名站映射和组合出口。
2. 计算**两个解压后 CSV 文件**的 SHA-256，创建规则副本并更新 `expected_sha256`。若数据变更使表行数变化，在副本里填写审核后的 `expected_counts`。生成器的行数报错会显示计算值与预期值，用于定位变化。新增或移除站点可能使排序分配的 ID 发生变化。
3. 先向独立目录输出生成结果。如果用于维护正式基线，待测试库验证通过后，用新版 ZIP 替换 `source-data/Archive.zip`，用规则副本替换 `config/data-rules.json`，再从项目根目录运行 `python -X utf8 tools/generate_import.py`。把这两项输入和生成的 `sql/import.sql`、`sql/queries.sql` 一起提交。若变更课程基线，复核报告中的计数、截图与固定课程测试预期。独立数据版本可以继续使用自己的数据包和规则。

```powershell
# 此目录内的两个 CSV 已编辑并保存为 UTF-8。按实际路径修改。
$inputDir = 'C:\work\metro-input'
Get-FileHash -Algorithm SHA256 "$inputDir\shenzhen_stations.csv", "$inputDir\station_exits.csv"
Compress-Archive -LiteralPath "$inputDir\shenzhen_stations.csv", "$inputDir\station_exits.csv" `
  -DestinationPath "$inputDir\updated.zip" -Force
Copy-Item config/data-rules.json "$inputDir\data-rules.json"
# 更新规则副本中的哈希及受影响的目标行数后执行。
$outputDir = Join-Path $inputDir 'preview'
python -X utf8 tools/generate_import.py --archive "$inputDir\updated.zip" `
  --rules "$inputDir\data-rules.json" --output $outputDir

# 用新建库预演，保留当前 metro_test 数据。
& "$pgBin\createdb.exe" -h 127.0.0.1 -p 55437 -U metro metro_preview
& "$pgBin\psql.exe" -X -h 127.0.0.1 -p 55437 -U metro -d metro_preview `
  -v ON_ERROR_STOP=1 -f "$outputDir\sql\import.sql"
python -X utf8 tools/verify_import.py --psql "$pgBin\psql.exe" --database metro_preview `
  --archive "$inputDir\updated.zip" --rules "$inputDir\data-rules.json" --data-only
```

`--data-only` 对照本次 CSV 逐行逐列检查六表。`generated/audit.json` 是生成审计，`generated/source_mapping.json` 记录原行到目标 ID 的映射。两者都可重新生成。基线完整验证可对专用库运行 `python -X utf8 tools/verify_import.py --psql "$pgBin\psql.exe" --database metro_preview`，该模式会重复导入并执行课程断言和约束测试。

## 4. 改现有数据库或改表结构

| 目标 | 做法 |
|---|---|
| 调整已有站点、线路和站序 | 用 Web 或 CLI 对当前库操作。跨站序更新会在一个事务里完成。先备份要保留的修改。 |
| 修改出口、地标等基线数据 | 按上一节改 CSV 并重新生成。如果只改当前库，可由库所有者在 DataGrip 或 `psql` 执行限定目标的 SQL。 |
| 新增字段、修改约束、索引或函数 | 修改 `sql/schema.sql`、`sql/indexes.sql` 或 `sql/functions.sql`。检查 `tools/generate_import.py` 的转换和列清单、`sql/q*.sql` 以及 Java 读写逻辑是否也需更新。 |
| 将结构变化应用到已有数据 | 先备份，编写针对现有结构的 `ALTER TABLE` 等迁移 SQL，在备份恢复库验证后再执行。上线前重新生成 `import.sql`，让新建库也使用新结构。 |

手工调试写入可先执行 `BEGIN;`，核对 `UPDATE ... WHERE ... RETURNING ...;` 的影响范围，再用 `COMMIT;` 保存或 `ROLLBACK;` 撤销。本地网页的 SQL 控制台只开放查询。变更 DDL 后，用 `python -X utf8 tools/check_design.py --psql "$pgBin\psql.exe" --database metro_preview` 核对设计图、报告字段字典和实库目录。基线的站、线增删改及站序操作示例也可参照 [答辩操作](defense-guide.md)。

## 5. 安装或更新票价表

将实际票价整理为 UTF-8 CSV，保存为 `config/fare.csv` 或工作目录中的文件。第一行固定为下列内容。

```csv
origin_station_id,destination_station_id,amount
```

每行是一对有向车站 ID 和 CNY 金额。同一方向只填一次，双向有记录时分成两行。站点 ID 使用当前库的 `project1.station.station_id`，金额精度到分、范围 0–9999.99。可先查询 `SELECT s.station_id,s.name_zh,d.name_en FROM project1.station s JOIN project1.district d USING (district_id) ORDER BY 1;`。数据版本变化后按“中文站名 + 行政区”重新匹配 ID，检查双向记录。仓库提供加载接口，实际金额由使用者提供。

```powershell
$env:METRO_FARE_CSV = (Resolve-Path config/fare.csv).Path
.\scripts\run.ps1 -Web
# 在另一个设置了同一环境变量的终端可执行无交互票价查询。
# 先把 419、420 换成票价文件中已有记录的出发站和到达站。
java -jar app/build/metro.jar --action fare start=419 end=420
```

应用在启动时读取 `METRO_FARE_CSV`，更新文件后重启。网页入口为「路线查询 → 查询票价」，CLI 为第 17 项。未配置或缺少该方向记录时，接口返回 `available=false`。`import.sql` 用于导入基础地铁数据，票价 CSV 由 Java 单独加载。 [FareTable.java](../app/src/main/java/metro/FareTable.java)

## 6. 数据库乱了怎么恢复

先选择恢复目标。**回到课程基线**使用 Git 中确认过版本的 `sql/import.sql`，会丢弃这六张表内的后续操作。**恢复自己的数据**使用出问题前的 PostgreSQL 备份。若仍可连接，先备份当前状态，便于找回要保留的修改。

### 保存当前库与恢复备份

用安装目录里的 `pg_dump` 和 `pg_restore`。将 `$backupDir` 改为项目目录之外的路径。以下备份整个 `metro_test`，包括它的其他 schema。票价 CSV 和 `config/db.properties` 是库外文件，单独保管。

```powershell
$backupDir = 'C:\work\metro-backups'
New-Item -ItemType Directory -Force $backupDir | Out-Null
$backupFile = Join-Path $backupDir ('metro_test-' + (Get-Date -Format yyyyMMdd-HHmmss) + '.dump')
& "$pgBin\pg_dump.exe" -h 127.0.0.1 -p 55437 -U metro -d metro_test -Fc -f $backupFile

# 把 $backupFile 设为要恢复的备份文件，再创建一个未使用的库名。
& "$pgBin\createdb.exe" -h 127.0.0.1 -p 55437 -U metro metro_restored
& "$pgBin\pg_restore.exe" -h 127.0.0.1 -p 55437 -U metro -d metro_restored `
  --single-transaction --no-owner $backupFile
```

确认备份命令退出码为 0，再继续后续操作。恢复到新库后核验站点数和要保存的业务记录，将应用的 `METRO_DB_URL` 指向 `jdbc:postgresql://127.0.0.1:55437/metro_restored` 后重启。跨实例恢复前先准备备份引用的角色，例如 `metro_sql_reader`。本项目新实例可用 `local-db.ps1 -Action sql-reader` 为 `metro_test` 初始化该角色。如改用 `--no-privileges` 恢复，恢复后再向单独的网页查询角色授予项目表读取权限。 [PostgreSQL 恢复工具文档](https://www.postgresql.org/docs/current/app-pgrestore.html)

### 恢复课程数据

若当前 `sql/import.sql` 指的是要恢复的基线，执行以下命令。若已修改基线，可在另一个目录检出对应提交，使用其 `sql/import.sql`，先在新建验证库核对。按表重建时 PostgreSQL 会检测外部依赖，出现错误会整笔回滚，先解决提示的依赖再重试。

```powershell
.\scripts\local-db.ps1 -Action start -PgBin $pgBin
.\scripts\local-db.ps1 -Action import -PgBin $pgBin
java -jar app/build/metro.jar --action q1
java -jar app/build/metro.jar --action q2
```

若项目实例的数据目录损坏、无法启动，先核对 `.runtime/pgdata` 确属当前项目且 PostgreSQL 已停止。把这个目录移动到项目外的备份位置，再用 `start` 创建新实例，随后从备份恢复或执行 `import` 初始化。避免在服务运行时移动数据目录。使用与新实例版本配套的服务端二进制文件。只有 SQL 基线的情况下可恢复课程数据，先前应用内的增删改需要有效备份才能恢复。

## 7. 测试、打包与配图

`./scripts/test.ps1` 运行 Python、Java 和可用的 Node 测试。`./scripts/test.ps1 -Integration` 会执行真实数据库读写，应通过 `METRO_DB_URL` 指向从基线导入的专用测试库。`./scripts/package.ps1` 构建交付包，排除本机数据库和私密配置。`python -X utf8 tools/benchmark.py --psql "$pgBin\psql.exe"` 生成查询计时和存储用量采样。

正式报告在 [CS307_Project1_Report.pdf](ER_lecture7/CS307_Project1_Report.pdf)，[TeX 源码目录](ER_lecture7/report-src/) 含原色配图及实机截图。[draw.io 概念 E-R 图源文件](ER_lecture7/概念ER图_drawio.drawio) 可直接编辑。修改图后，把新版 PNG 导出到 `ER_lecture7/report-src/figures/concept-er.png`，按 [报告编译说明](ER_lecture7/report-src/README.md) 重编译。
