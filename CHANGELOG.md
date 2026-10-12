# Changelog

本项目所有值得注意的变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

变更类型图例：

- `Added` —— 新增功能
- `Changed` —— 已有功能的行为或结构调整
- `Fixed` —— 缺陷修复
- `Removed` / `Deprecated` / `Security` —— 移除 / 弃用 / 安全相关

---

## [Unreleased]

暂无。

---

## [1.3.0] - 2026-10-12

重构为 **MVC + Service / Repository** 分层，并实装 **JWT + RBAC** 鉴权体系。

### Added

- 标准 MVC 分层：`controllers/`（路由）、`services/`（业务逻辑）、`repositories/`（纯数据访问）、`views/`（响应拼装 + 统一响应）、`models/`（ORM）、`core/`（横切）。
- RBAC 鉴权：`@auth_required` / `@require_role` / `@require_permission` 装饰器，基于 JWT（仅含身份 `sub` / `username`）；权限每次按 `sub` 查库，改动即时生效。
- `seed_rbac.py`：初始化权限目录、预置角色（`super_admin` / `admin` / `teacher` / `student`）与初始管理员。
- `requirements.txt` 增加 `PyJWT`、`bcrypt`（认证相关），移除未使用的 `openpyxl`。
- 新增 `REFACTOR_MVC.md`（重构说明）、`RBAC_USAGE.md`（权限与角色手册）、`RBAC_TEST.md`（鉴权回归用例）。

### Changed

- 业务逻辑（密码哈希、RBAC 守卫、唯一性 / 外键校验、删除保护）从原 `crud/` 抽到 `services/`；响应拼装（`*_to_out`）集中到 `views/serializers.py`。
- 原 `app/api/` → `app/controllers/`、`app/crud/` → `app/repositories/`、`app/core/response.py` → `app/views/response.py`，旧目录已删除。
- 日志模块由 `log_config.py` 更名为 `logger.py`，改为 `RotatingFileHandler`（单文件 10MB / 保留 5 备份）。

### Security

- `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` 已生效；`REFRESH_TOKEN_EXPIRE_MINUTES` 为 refresh_token 生成函数所用，登录接口当前仅签发 access_token。

---

## [1.2.0] - 2026-10-09

引入标准的环境变量配置体系，配置项集中到项目根目录的 `.env`，并让接口文档中的端口与实际配置自动同步。

### Added

- 新增 `.env`：本地实际配置（`APP_NAME`、`DEBUG`、`APP_HOST`、`APP_PORT`、`DATABASE_URL`、JWT 配置项等），已被 `.gitignore` 忽略。
- 新增 `.env.example`：配置模板，敏感值以 `your_password_here`、`sk-xxxxxxxx` 等占位符给出；复制为 `.env` 即可使用。
- 新增 `.gitignore`：忽略 `.env`、`venv/`、`__pycache__/`、`*.pyc`、`.pytest_cache/`。
- `app/core/config.py` 新增 `DATABASE_URL` 字段：提供时优先使用，未提供则回退到 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` 拼接（`database_url` 属性）。
- `app/core/config.py` 新增 JWT 配置：`SECRET_KEY`、`ALGORITHM`、`ACCESS_TOKEN_EXPIRE_MINUTES`、`REFRESH_TOKEN_EXPIRE_MINUTES`。（后于 [1.3.0] 正式接入鉴权；`REFRESH_TOKEN_EXPIRE_MINUTES` 为 refresh_token 生成函数所用，登录接口当前仅签发 access_token。）

### Changed

- `app/core/config.py`：`.env` 路径改为**锚定项目根目录**（`Path(__file__).resolve().parents[2]`），不再受启动时工作目录影响。
- `app/main.py`：`uvicorn.run()` 的 host / port / reload 改为读取 `settings.APP_HOST` / `APP_PORT` / `DEBUG`。
- `app/main.py`：模块说明与 Swagger 的 `contact` 链接改为按 `settings.APP_PORT` 动态生成，不再硬编码端口。
- `APP_PORT` 默认值保持 `8001` 不变，避免改变既有行为。

### Fixed

- 修复文档与实际端口不一致的问题：`main.py` 顶部的接口文档地址、`contact` 链接原先写死 `8000`，而实际默认端口为 `8001`，现统一由配置驱动。

> 说明：项目未接入 AI 调用，故未添加 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`。
> `core/forwarder.py` 中的 `127.0.0.1` 按计划保留硬编码（容器化部署时再抽为 `INTERNAL_BASE_URL`）。

---

## [1.1.0] - 2026-10-09

**MVC 三层架构重构**：将散落在 Controller 层的业务逻辑、数据拼装与聚合 SQL 全部下沉到 Model 层，使 Controller 只负责「收请求 → 调 Model → 返回」。

本次重构遵循**对外契约不变**原则：API 路径、请求参数、响应体结构与状态码全部保持原样，仅调整内部代码归属。

### Added

- 新增 `app/crud/stats.py`：承接原 `api/stats.py` 中 6 个统计接口的全部聚合 SQL 与 Python 运算（`CRUDStats` 类 + `crud_stats` 单例）。
- 新增 `app/schemas/stats.py`：6 个统计接口的响应模型（`OverviewOut`、`ClassCountOut`、`AvgScoreOut`、`EmploymentRateOut`、`ScoreRankingOut`、`TopSalaryOut`）。
- 新增 `app/core/forwarder.py`：从 `api/gateway.py` 抽出的转发编排逻辑（端口探测、httpx 调用、错误短路、状态码归一），因与数据库无关故置于 `core/` 而非 `crud/`。
- `app/crud/__init__.py` 导出 `crud_stats`，`app/schemas/__init__.py` 导出统计相关 Schema。
- 全部业务路由补充显式 `response_model=ApiResponse[...]`（共 36 条），使 View 层契约真正落到运行时。

### Changed

- `app/api/stats.py`：286 行 → 106 行，聚合逻辑整体迁出，每个路由精简为一次 `crud_stats.*` 调用 + `success()` 包装。
- `app/api/class_.py`、`student.py`、`teacher.py`、`score.py`、`employment.py`：移除 `_to_out()` 数据拼装、外键存在性预校验、`create` 后的二次重查、`exclude_unset` 判断、删除/恢复守卫，改为只声明路由与调用 CRUD。
- `app/crud/class_.py`、`student.py`、`teacher.py`、`score.py`、`employment.py`：承接上述逻辑，新增 `search()` / `get_detail()` / `create_x()` / `update_x()` / `delete_x()` / `restore_x()` 业务方法，直接返回拼装好的响应字典。
- 业务规则归属调整：「班级下还有学生时禁止删除」由 `crud/class_.py` 承担（原先由 Controller 编排）。
- `create` 类接口统一返回 HTTP `201`，响应体 `code` 同步为 `201`（行为与重构前一致）。
- 删除类接口的 `data` 保留实体主键名（`student_id` / `class_id` / …），未统一为 `id`。

### Fixed

- 清理 `app/core/exceptions.py`、`app/api/deps.py`、`app/schemas/student.py` 等文件中的未使用导入（pyflakes 检出）。
- 修复 IDE 全线标红：PyCharm 以 `app/` 为项目根且未标记 Sources Root，导致 117 处 `from app.` 导入无法解析；在 `app/.idea/app.iml` 中将上级目录添加为内容根与 Sources Root 后恢复正常。

### 刻意保持不变的行为

以下两点属于重构前的既有实现，虽不够理想但会影响返回值，故本次**不擅自修改**，仅在此登记：

- `GET /stats/employment-rate`：学生数为 0 时只返回 3 个键，非 0 时返回 4 个键（少 `unemployed_count`）。通过路由上的 `response_model_exclude_unset=True` 维持原样。
- `GET /stats/overview`：无成绩记录时 `avg_score` 为 `null`，而非 `0`。

### 验证

- 端点数 39 → 39，路径与方法集合完全一致。
- SQLite + `TestClient` 回归用例 **35/35 通过**（覆盖 5 张表的增删改查、逻辑删除与恢复、唯一性冲突、外键校验、6 个统计接口及网关转发）。
- `python -m compileall app` 通过，pyflakes 无新增告警。

---

## [1.0.0] - 2026-10-09

初始版本：基于 FastAPI + SQLAlchemy 2.0 + MySQL 的学生管理系统后端。

### Added

- 五张业务表（班级 `class`、学生 `student`、教师 `teacher`、成绩 `score`、就业 `employment`）的完整 RESTful 接口，共 39 个端点。
- 统一响应格式 `{code, message, data}` 与全局异常处理（`BusinessException` / `HTTPException` / 参数校验 / 500 兜底）。
- 全表逻辑删除（`is_deleted`）与回收站恢复接口。
- 基于 `unique_specs` 的唯一性校验，命中返回 409。
- 6 个统计分析接口（`/stats/overview`、`/class-count`、`/avg-score`、`/employment-rate`、`/score-ranking`、`/top-salary`）。
- `POST /gateway` 内部转发网关：供 Dify 对话流的 HTTP 节点调用，恒返回 HTTP 200，真实状态码由响应体 `code` 承载。
- 请求字段格式校验（姓名、通用文本、数值范围等）。
- 服务启动时自动建表（`Base.metadata.create_all()`）。

---

> 各版本的对比链接待仓库接入远程 Git 托管后补充。
