# 深圳地铁数据管理 · CS307 Project 1

本项目将两份深圳地铁课程 CSV 转换为 PostgreSQL 六表。Java 应用提供交互式 CLI 和本地网页，可维护车站、线路及站序，核验导入结果，查询路径、地标和已配置的票价。

**[从零构建与维护指南](docs/setup-and-operations.md)** 汇总 Windows 安装、所有 CLI 和 HTTP 动作、SQL 入口、CSV 更新、改库迁移、票价导入、备份与恢复。

## 项目文件

| 路径 | 内容 |
|---|---|
| `app/src/` | Java 应用、网页资源和测试。 [`Java 构建与站点 CRUD`](docs/java-build-and-crud.md) |
| `sql/` | 建表、导入、索引、查询和只读账号配置。 |
| `source-data/Archive.zip` | 两份课程 CSV 的原始数据包。 |
| `config/` | 数据映射规则及数据库连接示例。 |
| `scripts/`、`tools/`、`tests/` | 构建、运行、数据库管理、生成器及验证工具。 |
| `docs/` | 维护及答辩指南、报告、ER 图与可编辑图源。 |

## 报告与演示

- [课程项目报告 PDF](docs/ER_lecture7/CS307_Project1_Report.pdf) · [TeX 源码和编译说明](docs/ER_lecture7/report-src/)
- [概念 E-R 图](docs/ER_lecture7/report-src/figures/concept-er.png) · [draw.io 图源](docs/ER_lecture7/概念ER图_drawio.drawio) · [PostgreSQL 六表关系图](docs/ER_lecture7/report-src/figures/datagrip-schema.png)
- [一键导入、Q1–Q7 与站序演示](docs/defense-guide.md)
