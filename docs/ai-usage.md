# 脚本与AI辅助记录

以下按实际交付列出。正式课程报告中的作者/使用者须由组员填写真实姓名、任务和贡献比例；不能用AI替代成员署名。

| 名称 | 类型 | 作用与运行 |
|---|---|---|
| tools/generate_import.py | Python脚本 | `python tools/generate_import.py`，校验源哈希、解析CSV与组合出口、生成完整import.sql及源行映射 |
| sql/schema.sql / indexes.sql / functions.sql | SQL源文件 | 六表结构、附加索引及Q7函数；完整执行优先使用已包含这些内容的import.sql |
| sql/import.sql | 独立SQL脚本 | 在专用作业库中以DataGrip执行；包含全部DDL、INSERT、断言、序列同步、ANALYZE与事务 |
| sql/queries.sql | SQL脚本 | DataGrip默认参数的Q1–Q7现场核验 |
| scripts/build.ps1 / run.ps1 | PowerShell脚本 | 构建JAR及启动CLI/本地网页 |
| scripts/local-db.ps1 | PowerShell脚本 | 管理本项目专用本地PostgreSQL实例，显式执行导入 |
| scripts/test.ps1 | PowerShell脚本 | 运行单元测试与可选真实数据库/HTTP集成验证 |
| scripts/package.ps1 | PowerShell脚本 | 打包源码、生成文件和运行JAR，排除私密配置及数据库目录 |
| Codex | AI编程助手 | 辅助需求分析、数据核验、数据库与程序设计、代码实现、测试、说明文档和独立代码审查 |

模型具体标识请从本次会话界面/实际记录填写，不以推测型号代替。AI输出仍需两位组员理解、复核并按课程规则披露。原CSV未以外部资料覆盖。没有下载、复制网络图示或他人作业代码。

技术参考（机制核对，不是抄写课程报告）：

- [PostgreSQL 12 CREATE TABLE](https://www.postgresql.org/docs/12/sql-createtable.html)：延迟唯一约束和外键。
- [pgJDBC 官方下载](https://jdbc.postgresql.org/download/)：运行驱动42.7.14，随包驱动SHA-256为`73914527305a40cce504b0d3d90b23caf565136912d607ae8ae7c5895512332c`；许可证见JAR内META-INF/LICENSE，原样保留。
- [JDK 17 HttpServer](https://docs.oracle.com/en/java/javase/17/docs/api/jdk.httpserver/com/sun/net/httpserver/HttpServer.html)：本地HTTP入口。
