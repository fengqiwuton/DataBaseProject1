# E-R 图源与数据库关系说明

2026-11-02新增：按Lecture 7课堂表示法绘制的正式概念图、六表映射图及完整设计理由位于[ER_lecture7目录](ER_lecture7/ER设计思路与项目要求对应说明.md)。下方Mermaid保留为关系结构参考，不能混同为课堂概念表示法。


以下为可编辑的逻辑图源，可在支持 Mermaid 的软件中查看。正式报告配图和说明见 [Report Task 1–2](report-task1-task2.md)，其中包含课程表示法概念图和 DataGrip 从 PostgreSQL 实库导出的关系图。


```mermaid
erDiagram
    district ||--o{ station : contains
    station ||--o{ line_station : serves
    metro_line ||--o{ line_station : includes
    station ||--o{ station_exit : has
    station_exit ||--o{ exit_landmark : reaches
    district {
        integer district_id PK
        text name_en UK
    }
    station {
        integer station_id PK
        integer district_id FK
        text name_zh "联合唯一(name_zh,district_id)"
        text name_en
        integer lon_mdeg
        integer lat_mdeg
    }
    metro_line {
        integer line_id PK
        text name_zh UK
        text name_en UK
    }
    line_station {
        integer line_id PK,FK
        integer station_id PK,FK
        integer position "联合唯一(line_id,position)，可延迟"
        text status
        smallint opening_year
        time first_train
        time last_train
    }
    station_exit {
        integer exit_id PK
        integer station_id FK
        text exit_code "联合唯一(station_id,exit_code)"
    }
    exit_landmark {
        integer exit_id PK,FK
        text landmark_name PK
    }
```

所有实体均参与至少一条外键关系。FK方向：exit_landmark→station_exit→station→district，line_station→station和metro_line，无环。每表均有非自增ID的必填业务字段；关联表的复合主键本身提供非自增业务唯一性。

DataGrip：连接作业库→执行 import.sql→刷新 project1 schema→选择该 schema→Show Diagram（部分版本称 Show Visualization）→调整布局并导出 PNG。完整字段定义以 `sql/schema.sql` 为准。
