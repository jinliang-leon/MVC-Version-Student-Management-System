# WorkBuddy 学生管理系统

面向教务场景的后端服务：用 RESTful 接口管理**班级、学生、教师、成绩、就业**五张业务表，内置 **JWT + RBAC** 鉴权与角色权限体系，并接入 Dify 对话流，让用户用自然语言完成数据的增删改查。

## 技术栈

| 方向 | 选型 |
|---|---|
| Web 框架 | FastAPI |
| ASGI 服务器 | Uvicorn（`uvicorn[standard]`） |
| ORM | SQLAlchemy 2.0（`Mapped` / `select()` 新风格） |
| 数据校验与配置 | Pydantic v2、pydantic-settings |
| 数据库 | MySQL 8 + PyMySQL 驱动 |
| 认证鉴权 | PyJWT（签发/校验 Token）+ bcrypt（密码哈希） |
| 日志 | 标准库 `logging` + 滚动文件 handler |
| 内部转发 | httpx（Dify `/gateway` 自转发） |

完整依赖见 [`app/requirements.txt`](app/requirements.txt)。

## 目录结构

```
学生管理系统与dify/
├── .env                      # 本地环境变量（含敏感信息，已被 .gitignore 忽略）
├── .env.example              # 环境变量模板
├── .gitignore
├── .dockerignore
├── Dockerfile                # 后端镜像（构建上下文为项目根目录）
├── docker-compose.yml        # 后端 + MySQL 一键编排
├── seed_rbac.py              # RBAC 种子脚本：建表 + 初始化权限/角色/初始管理员
├── API.md / ARCHITECTURE.md / DATABASE.md / CHANGELOG.md
└── app/                      # 唯一的 Python 包
    ├── main.py               # 应用入口：创建 FastAPI 实例、挂载路由与全局异常处理
    ├── requirements.txt
    ├── api/                  # 【Controller 层】路由函数：收请求 → 调 CRUD → 返回
    ├── core/                 # 基础设施：配置、数据库、安全、鉴权装饰器、日志、响应、转发
    ├── models/               # 【Model 层】SQLAlchemy ORM 表结构
    ├── schemas/              # Pydantic 模型：入参校验 + 出参结构（View 层）
    ├── crud/                 # 【Model 层】数据访问与业务逻辑
    └── logs/                 # 运行时日志输出（已被 .gitignore 忽略）
```

### 各层职责

- **`api/`（Controller）** —— 只做参数声明、调用一次 `crud`、用 `success()` 包装返回；不含 SQL，不含业务规则。业务接口通过装饰器声明所需权限码。
  - `class_.py` `student.py` `teacher.py` `score.py` `employment.py`：五张业务表的标准 CRUD
  - `auth.py`：登录、注册、当前用户（`/auth`）
  - `users.py` `roles.py` `permissions.py`：RBAC 用户/角色/权限管理
  - `stats.py`：6 个统计接口
  - `gateway.py`：Dify 专用转发入口
  - `deps.py`：数据库会话与分页参数依赖
- **`models/`（Model）** —— ORM 表结构。`base.py` 的 `TimestampMixin` 为每张表统一注入 `created_at` / `updated_at` / `is_deleted`；`role.py` 中定义 `user_role`、`role_permission` 两张多对多关联表。
- **`crud/`（Model）** —— `base.py` 是泛型 `CRUDBase`（分页、模糊搜索、唯一性校验、逻辑删除/恢复）；各实体文件在此实现自身业务规则与字段拼装（如给成绩补上 `student_name`）。
- **`schemas/`（View）** —— `*Out` 类定义接口返回的 JSON 结构，通过路由上的 `response_model=ApiResponse[X]` 约束输出；`*Create` / `*Update` 负责入参校验；`auth.py` / `rbac.py` 为鉴权相关结构。
- **`core/`（基础设施）** —— `config.py` 读取 `.env`、`database.py` 管理引擎与会话、`security.py` 密码哈希与 JWT 编解码、`decorators.py` 鉴权装饰器、`log_config.py` 日志初始化、`response.py` 统一响应体与全局异常处理、`forwarder.py` 自转发逻辑。

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

数据库只需先建好一个空库，**表不用手动建**：服务启动时会执行 `Base.metadata.create_all()` 自动创建/补齐全部业务表与 RBAC 表。

> `requirements.txt` 中的 `openpyxl` 目前未被代码直接引用，属预留依赖；`cryptography` 是 PyMySQL 连接 MySQL 8 默认认证插件（`caching_sha2_password`）时所需的依赖，不建议移除。

## 环境变量配置

```bash
cp .env.example .env
```

然后编辑 `.env`，至少改这两项：

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | 完整连接串，例：`mysql+pymysql://root:你的密码@127.0.0.1:3306/student_management?charset=utf8mb4` |
| `SECRET_KEY` | JWT 签名密钥，**务必改为强随机值**。生成：`python -c "import secrets; print(secrets.token_hex(32))"` |

常用可选项：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_NAME` | 学生管理系统 | 服务名称 |
| `DEBUG` | `True` | 开发模式（会打印 SQL） |
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8001` | 监听地址与端口 |
| `ALGORITHM` | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token 有效期（分钟） |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | 初始管理员账号，供 `seed_rbac.py` 使用 |
| `CORS_ORIGINS` | `*` | 允许的跨域来源，多个用逗号分隔 |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `10` / `100` | 分页默认与最大条数 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `LOG_DIR` / `LOG_FILE` | `app/logs` / `app.log` | 日志目录与文件名（相对路径以项目根目录为基准） |
| `LOG_ROTATION` | `time` | 切分方式：`time` 按天 / `size` 按大小 |
| `LOG_BACKUP_COUNT` | `30` | 保留的备份数（time 模式下约等于保留天数） |
| `LOG_MAX_BYTES` | `10485760` | size 模式下单个文件最大字节（10MB） |

说明：

- `.env` 路径固定锚定在项目根目录（见 `app/core/config.py`），不受启动时工作目录影响。
- 若不用 `DATABASE_URL`，可改用 `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` 分字段拼接（`.env.example` 中已注释给出）；两者同时存在时 **`DATABASE_URL` 优先**。
- 真实环境变量优先级高于 `.env`，可临时覆盖，例如 `APP_PORT=9000 python -m app.main`。

## 初始化 RBAC 数据

建表由服务启动自动完成，但**权限目录、预置角色、初始管理员需要跑一次种子脚本**：

```bash
python seed_rbac.py       # 在项目根目录执行
```

脚本是幂等的：已存在的权限/角色会跳过，角色的权限映射会收敛到脚本中定义的状态，可重复执行。默认创建管理员 `admin / admin123`（取自 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）并授予 `super_admin` 角色；若仍在使用默认密码，脚本会打印警告。**生产环境请先改密码再执行。**

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

调业务接口前先在 `/auth/login` 拿到 Token，再点 Swagger 右上角的 **Authorize** 填入（`persistAuthorization` 已开启，刷新页面不用重填）。Swagger 里所有接口都会显示锁图标（安全方案是全局声明的），但白名单接口（`/auth/login`、`/auth/register`、`/health` 等）实际仍可匿名访问。

## 鉴权说明

采用 **JWT + RBAC**，通过装饰器而非 FastAPI 依赖注入实现（见 `app/core/decorators.py`）：

| 装饰器 | 作用 | 失败时 |
|---|---|---|
| `@auth_required` | 校验 `Authorization: Bearer <token>`，把用户对象挂到 `request.state.user` | 401 |
| `@require_role("admin")` | 在鉴权基础上校验角色码，**严格匹配**（超级管理员不会自动等于 `admin`） | 403 |
| `@require_permission("student:delete")` | 在鉴权基础上校验权限码；拥有 `is_system` 角色（超级管理员）则直接放行 | 403 |

要点：

- 权限码以**数据库为准实时加载**，改动角色权限后立即生效，无需重新登录。JWT 里虽然也带了 `roles`，但只供前端展示与轻量判断。
- 鉴权失败的响应同样走统一格式 `{code, message, data}`，`code` 为 401 / 403。
- 被装饰的路由函数必须带 `request: Request` 参数（装饰器从其中取 Token）。

### 权限码

权限由 `seed_rbac.py` 维护，共 41 个，接口层只读（`/permissions`）。命名规则 `模块:动作`：

| 模块 | 权限码 |
|---|---|
| `class` `student` `teacher` `score` `employment` | `list` `read` `create` `update` `delete` `restore` |
| `stats` | `view` |
| `role` | `list` `read` `create` `update` `delete` `assign-permission` |
| `permission` | `list` |
| `user` | `list` `read` `assign-role` |

### 预置角色

| 角色码 | 名称 | 权限范围 |
|---|---|---|
| `super_admin` | 超级管理员 | 全部权限（`is_system`，鉴权时直接放行） |
| `admin` | 管理员 | 五张业务表全部操作 + 统计 + 权限查看 + 用户管理；**不含角色管理** |
| `teacher` | 教师 | 班级/学生/教师/就业**只读** + 成绩全部操作 + 统计查看 |
| `student` | 学生 | 五张业务表全部**只读** + 统计查看 |

## 响应格式

所有业务接口统一返回以下结构，HTTP 状态码与 `code` 一致（`/gateway` 除外，见下）：

```json
{ "code": 200, "message": "success", "data": {} }
```

新增接口返回 HTTP `201`；删除为逻辑删除，数据保留、可通过 `restore` 恢复；列表与详情接口支持 `include_deleted=true` 查询已删除数据。

## 接口一览

除 `/auth/login`、`/auth/register`、`/health`、`/`、`/gateway` 外，**所有接口都需要 Bearer Token 且校验对应权限码**。

| 路由前缀 | 接口 |
|---|---|
| `/auth` | `POST /login`、`POST /register`（均免鉴权）、`GET /me` |
| `/classes`、`/students`、`/teachers`、`/scores`、`/employments` | `GET /`（分页列表）、`GET /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`、`POST /{id}/restore` |
| `/stats` | `/overview`、`/class-count`、`/avg-score`、`/employment-rate`、`/score-ranking`、`/top-salary` |
| `/roles` | `GET /`、`GET /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`、`PUT /{id}/permissions`（分配权限） |
| `/permissions` | `GET /`（按模块分组，只读） |
| `/users` | `GET /`（分页）、`GET /{id}`、`PUT /{id}/roles`（分配角色） |
| `/`、`/health` | 服务信息、健康检查 |
| `/gateway` | Dify 转发入口（见下） |

详细字段与示例见 [API.md](API.md)。

## 日志

`main.py` 启动时调用 `setup_logging()` 完成一次性初始化：**控制台 + 文件双输出**，全局统一格式。

```
2026-10-12 09:30:00 | INFO     | app.main:50 | 数据库表检查/创建完成
```

- 输出位置：默认 `<项目根>/app/logs/app.log`（由 `LOG_DIR` / `LOG_FILE` 控制，相对路径锚定项目根目录）。
- 滚动策略：默认按天切分（`LOG_ROTATION=time`，午夜切分，保留 30 天）；改为 `size` 则按 `LOG_MAX_BYTES` 切分，保留 `LOG_BACKUP_COUNT` 个备份。
- 业务代码统一用 `logger = logging.getLogger(__name__)` 取模块级 logger，用 `%s` 惰性拼接；只有处于 `except` 分支才用 `exc_info=True`。

## Docker 部署

`docker-compose.yml` 已编排后端 + MySQL 8，开箱可用：

```bash
docker compose up -d --build

# 停止（保留数据）
docker compose down
# 停止并清空数据库数据
docker compose down -v
```

说明：

- 容器内通过服务名 `db` 访问 MySQL，`DATABASE_URL` 由 compose 的 `environment` 注入（优先级高于 `.env`），MySQL 密码在 compose 里以明文给出，**生产环境务必改掉**。
- `app` 服务 `depends_on` 了 `db` 的 `service_healthy`，MySQL 真正就绪后才会启动，避免建表失败。
- 日志通过命名卷 `app_logs` 持久化到容器内 `/app/app/logs`。
- `Dockerfile` 以非 root 用户 `appuser` 运行，镜像内建了日志目录；如改端口需同步改 `Dockerfile` 的 `EXPOSE`/`CMD` 与 compose 的端口映射。
- 首次部署还需初始化 RBAC 数据。镜像只 `COPY app /app/app`，**没有把 `seed_rbac.py` 复制进去**，所以不能直接 `docker compose exec app python seed_rbac.py`。两种可行做法：
  1. 在本机（已装依赖）指向容器里的 MySQL 执行，compose 已把 3306 映射到宿主机：
     ```bash
     DATABASE_URL="mysql+pymysql://root:123456@127.0.0.1:3306/student_management?charset=utf8mb4" python seed_rbac.py
     ```
  2. 或在 `Dockerfile` 中补一行 `COPY seed_rbac.py /app/seed_rbac.py` 后重新构建，再 `docker compose exec app python seed_rbac.py`。

## Dify 转发网关

`POST /gateway` 供 Dify 的 HTTP 请求节点调用。Dify 的 method 是固定枚举、无法用变量指定，因此这里用单一入口，按请求体里的 `method` + `path` 转发到本服务的内部路由：

```json
{ "method": "GET", "path": "/students/?gender=男", "body": {}, "error": "" }
```

- 该接口**恒返回 HTTP 200**，真实状态码放在响应体的 `code` 字段，避免 Dify 节点因 4xx/5xx 中断流程。
- 该接口本身**不校验 Token**（Dify 侧无需配置鉴权），但转发时会用服务账号 `_gateway_service`（首次调用自动创建，密码随机、不可登录，已授予 `super_admin`）现场签发一个内部 JWT，因此下游业务接口的权限校验照常生效。
- `path` 必须以 `/` 开头，且不允许携带协议或主机地址（`://`、`//` 会被拒绝）；转发目标地址取当前请求的端口，改端口后无需改配置。

## 管理后台

`main.py` 会在 `frontend/index.html` 存在时自动挂载 `/ui` 页面。当前仓库中尚无 `frontend/` 目录，该路由不会注册。
