# 概念 E-R 图（draw.io，Lecture 7 第 5 页形式）说明

本文件是同目录 `概念ER图_drawio.drawio` / `E-R_project1.png` 的配套说明。
图面按 **Lecture 7 第 5 页（The New Running Example）** 的形式绘制，**不含任何注释、图例或标题**；图例与口径全部写在本文。

## 1. 文件与绘图工具

| 文件 | 内容 |
|---|---|
| `概念ER图_drawio.drawio` | draw.io（diagrams.net）原生可编辑源文件——Task 1 的正式绘图 |
| `E-R_project1.png` | 由 **diagrams.net 自身的 viewer** 渲染导出（headless 浏览器打开 viewer 后截图并裁边），3423×1672 |
| `概念ER图_drawio说明.md` | 本文件 |

- **绘图软件（报告如实填写）**：diagrams.net / draw.io。
- **打开与编辑**：浏览器打开 `app.diagrams.net` → `File → Open From → Device` → 选择 `.drawio`。所有元素（实体框、表头、属性文本、菱形、连线、箭头）都是可编辑对象，连线已绑定到锚点，拖动图形会跟随。
- **导出图片（与交付 PNG 同一路径）**：`File → Export as → PNG`，Zoom 300%，取消 Transparent Background；也可导出 SVG/PDF 用于排版。
- **重新生成**：`python tools/draw_er_drawio.py`。脚本先写 `.drawio`，再用本机 Edge 打开 diagrams.net viewer 渲染并裁边成 PNG；若无 Edge 或无法联网，则退回内置的离线渲染器（Pillow，同一坐标模型），输出内容一致。

## 2. 记号（对应第 5 页的画法）

| 记号 | 含义 |
|---|---|
| 带浅蓝表头的矩形 | 实体集：表头是实体名，框内逐行列出属性 |
| 斜体文字 | 与第 5 页一致：实体名、属性名、联系名均为斜体衬线体（Times New Roman） |
| 属性下划线 | 主键（实线下划线） |
| 属性**虚**线下划线 | 弱实体的部分键（partial key） |
| **双矩形** | 弱实体集（weak entity set） |
| **双菱形** | 识别联系（identifying relationship） |
| 浅青色菱形 | 联系集，菱形内是斜体小写联系名 |
| **箭头** | 该方向上"至多一个"（函数式/多对一） |
| **双线** | 全参与（total participation） |
| 虚线 + 普通矩形 | 联系自身的描述属性 |
| `{ }` | 多值属性 |

第 5 页不使用 `l..h` 标注，本图同样不使用；基数只由箭头与双线表达。

**所有连线都是横平竖直的**（水平或垂直）：实体与菱形之间的连接点都对齐到同一 y 或同一 x，双线是两条平行的水平线或垂直线。图中唯一的斜边来自菱形本身。生成脚本里有 `check_orthogonal()` 断言，任何一次布局改动只要产生斜线就会直接报错，不会悄悄画出斜线。

## 3. 实体、属性与主键

| 图中实体 | 属性（下划线为主键） | 对应表 |
|---|---|---|
| district | <u>district_id</u>、name_en | `district` |
| station | <u>station_id</u>、name_zh、name_en、lon_mdeg、lat_mdeg | `station` |
| line | <u>line_id</u>、name_zh、name_en | `metro_line` |
| exit（**弱实体**） | exit_code（部分键，虚线下划线）、`{landmark_name}` | `station_exit` + `exit_landmark` |

概念名用英文短名（`line`、`exit`）以贴合第 5 页的写法，右边一列是它们在关系模式中的落点，报告里须把这张对照表一并给出。

## 4. 联系与基数（怎样读这张图）

| 联系（菱形） | 画法 | 含义 | 落点 |
|---|---|---|---|
| `station_district` | station 侧**双线**，指向 district 的**箭头** | 每个车站必须属于一个行政区（全参与），且至多属于一个（箭头指向"一"端） | `station.district_id` 非空外键，不另建表 |
| `line_station` | 两侧均为单线，无箭头 | 车站与线路多对多：一条线经过多站，一个站可属多线 | 独立 `line_station` 表；`position/status/opening_year/first_train/last_train` 是该联系的描述属性，画在虚线连接的矩形里 |
| `exit_station` | **双菱形**（识别联系）、exit 侧**双线**（全参与）、指向 station 的**箭头** | 出口不能独立存在：必须且只能属于一个车站，由「车站 + exit_code」识别 | `station_exit.station_id` 非空外键，不另建表 |

## 5. 几处可能被追问的画法

1. **出口按弱实体画**：出口不能脱离车站存在，它的身份是「所属车站 + exit_code」，因此用**双矩形**表示弱实体集、`exit_code` 用**虚线下划线**表示部分键、`exit_station` 用**双菱形**表示识别联系，出口侧再用双线表示全参与。数据库里的 `exit_id` 只是实现用的代理键（Task 2 的 DDL 仍以它为主键），概念层不画它——与「外键不画进 ER 图」是同一层区分，报告里要说明。
2. **地标用多值属性**：当前数据里地标只有名称，画 `{landmark_name}`，落为 `exit_landmark` 表；同名地标不代表同一地点，不合并。
3. **联系属性不重复画两端键**：`station_id`、`line_id` 在 `line_station` 的语义中已隐含，只在关系模式里显式出现。
4. **允许"零"参与**：车站可以不编入任何线路、线路可以先建后编站，因此 `line_station` 两侧都不是全参与（单线、无箭头对应的部分）。
5. **图中不写可空性、唯一约束、字段类型**：这些属于 Task 2 的 DDL 与字段说明（见 `sql/schema.sql` 与 `项目要求总结与技术实现路线.md` 第 5.1 节），写进概念图会把它变成实现图。

## 6. 与 Task 2 的衔接

- 独立 DDL：`sql/schema.sql`（`CREATE SCHEMA` + 六张 `CREATE TABLE`，可单独执行，无任何数据）。
- 概念到六表的映射图：同目录 `六表关系映射图.png/.svg`。
- 逐表逐字段解释：`项目要求总结与技术实现路线.md` 第 5.1 节字段字典，与 `sql/schema.sql` 逐列对应。
- **仍需组员完成**：Task 2 要求"数据库客户端生成的关系图截图"，须在 DataGrip 连接实库后选中六表 `Show Visualization` 导出；本目录的映射图是人工绘制图，不能冒充 DataGrip 截图。

## 7. 版本说明

同目录 `概念ER图_Lecture7.png/.svg` 是更早一版概念图（`l..h` 参与次数标注、出口按普通实体）。本版按第 5 页形式（箭头 + 双线）并把出口改画为**弱实体**；两版语义相同，提交只用一版。**提交时用本版一版即可**，不要两版同时提交。
