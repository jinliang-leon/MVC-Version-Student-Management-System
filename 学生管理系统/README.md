# WorkBuddy 学生管理系统

面向教务场景的后端服务：用 RESTful 接口管理**班级、学生、教师、成绩、就业**五张业务表，并接入 Dify 对话流，让用户用自然语言完成数据的增删改查。

## 技术栈

| 方向 | 选型 |
|---|---|
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn（`uvicorn[standard]`） |
| ORM | SQLAlchemy 2.0（`Mapped` / `select()` 新风格） |
| 数据校验与配置 | Pydantic v2、pydantic-settings |
| 数据库 | MySQL 8 + PyMySQL 驱动 |
| 内部转发 | httpx（Dify `/gateway` 自转发） |

完整依赖见 [`app/requirements.txt`](app/requirements.txt)。

## 目录结构

```
学生管理系统与dify/
├── .env                      # 本地环境变量（含敏感信息，已被 .gitignore 忽略）
├── .env.example              # 环境变量模板
├── .gitignore
└── app/                      # 唯一的 Python 包
    ├── main.py               # 应用入口：创建 FastAPI 实例、挂载路由与全局异常处理
    ├── requirements.txt
    ├── api/                  # 【Controller 层】路由函数：收请求 → 调 CRUD → 返回
    ├── core/                 # 基础设施：配置、数据库连接、统一响应、异常、转发
    ├── models/               # 【Model 层】SQLAlchemy ORM 表结构
    ├── schemas/              # Pydantic 模型：入参校验 + 出参结构（View 层）
    └── crud/                 # 【Model 层】数据访问与业务逻辑
```

### 各层职责

- **`api/`（Controller）** —— 只做参数声明、调用一次 `crud`、用 `success()` 包装返回；不含 SQL，不含业务规则。
  - `class_.py` `student.py` `teacher.py` `score.py` `employment.py`：五张表的标准 CRUD
  - `stats.py`：6 个统计接口
  - `gateway.py`：Dify 专用转发入口
  - `deps.py`：分页参数依赖
- **`models/`（Model）** —— ORM 表结构。`base.py` 的 `TimestampMixin` 为每张表统一注入 `created_at` / `updated_at` / `is_deleted`。
- **`crud/`（Model）** —— `base.py` 是泛型 `CRUDBase`（分页、模糊搜索、唯一性校验、逻辑删除/恢复）；各实体文件在此实现自身业务规则与字段拼装（如给成绩补上 `student_name`）。
- **`schemas/`（View）** —— `*Out` 类定义接口返回的 JSON 结构，通过路由上的 `response_model=ApiResponse[X]` 约束输出；`*Create` / `*Update` 负责入参校验。
- **`core/`（基础设施）** —— `config.py` 读取 `.env`、`database.py` 管理引擎与会话、`response.py` 提供统一响应体与全局异常处理、`forwarder.py` 实现自转发逻辑。

架构与分层理由详见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 环境搭建

要求：**Python 3.10+**、**MySQL 8**。

```bash
# 1. 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. 安装依赖（注意：requirements.txt 在 app/ 目录下）
pip install -r app/requirements.txt
```

数据库只需先建好一个空库，**表不用手动建**：服务启动时会执行 `Base.metadata.create_all()` 自动创建/补齐 5 张业务表。

> `requirements.txt` 中的 `openpyxl`、`cryptography` 目前未被代码直接引用，属预留依赖。

## 环境变量配置

```bash
cp .env.example .env
```

然后编辑 `.env`，至少改这一项：

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | 完整连接串，例：`mysql+pymysql://root:你的密码@127.0.0.1:3306/student_management?charset=utf8mb4` |

常用可选项：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_NAME` | 学生管理系统 | 服务名称 |
| `DEBUG` | `True` | 开发模式（会打印 SQL） |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8001` | 监听地址与端口 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源，多个用逗号分隔 |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `10` / `100` | 分页默认与最大条数 |
| `SECRET_KEY` / `ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` | — | JWT 预留配置，当前尚无代码消费 |

说明：

- `.env` 路径固定锚定在项目根目录（见 `app/core/config.py`），不受启动时工作目录影响。
- 若不用 `DATABASE_URL`，可改用 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` 分字段拼接（`.env.example` 中已注释给出）；两者同时存在时 **`DATABASE_URL` 优先**。
- 真实环境变量优先级高于 `.env`，可临时覆盖，例如 `APP_PORT=9000 python -m app.main`。

## 启动方式

在项目根目录执行：

```bash
uvicorn app.main:app --reload
```

或使用 `main.py` 内置入口（自动读取 `.env` 中的 `APP_HOST` / `APP_PORT` / `DEBUG`）：

```bash
python -m app.main
```

默认监听 **http://127.0.0.1:8001**，端口由 `APP_PORT` 决定。

## API 文档地址

| 地址 | 说明 |
|---|---|
| http://127.0.0.1:8001/docs | Swagger UI，可直接在线调试 |
| http://127.0.0.1:8001/redoc | ReDoc |
| http://127.0.0.1:8001/openapi.json | OpenAPI 原始描述 |

端口与 `APP_PORT` 保持一致：`main.py` 的模块说明和 Swagger 的 contact 链接均由该配置动态生成，改端口后文档自动同步。

### 响应格式

所有业务接口统一返回以下结构，HTTP 状态码与 `code` 一致（`/gateway` 除外，见下）：

```json
{ "code": 200, "message": "success", "data": {} }
```

新增接口返回 HTTP `201`；删除为逻辑删除，数据保留、可通过 `restore` 恢复；列表与详情接口支持 `include_deleted=true` 查询已删除数据。

### 接口一览

| 路由前缀 | 接口 |
|---|---|
| `/classes`、`/students`、`/teachers`、`/scores`、`/employments` | `GET /`（分页列表）、`GET /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`、`POST /{id}/restore` |
| `/stats` | `/overview`、`/class-count`、`/avg-score`、`/employment-rate`、`/score-ranking`、`/top-salary` |
| `/`、`/health` | 服务信息、健康检查 |

### Dify 转发网关

`POST /gateway` 供 Dify 的 HTTP 请求节点调用。Dify 的 method 是固定枚举、无法用变量指定，因此这里用单一入口，按请求体里的 `method` + `path` 转发到本服务的内部路由。

该接口**恒返回 HTTP 200**，真实状态码放在响应体的 `code` 字段，避免 Dify 节点因 4xx/5xx 中断流程。

### 管理后台

`main.py` 会在 `frontend/index.html` 存在时自动挂载 `/ui` 页面。当前仓库中尚无 `frontend/` 目录，该路由不会注册。
