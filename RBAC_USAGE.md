# 学生管理系统 · RBAC 鉴权模块使用说明

> 适用项目：`学生管理系统与dify`（FastAPI 后端）
> 本文档覆盖 RBAC 鉴权模块的**架构、表结构、权限点、角色对照、鉴权流程、装饰器用法、扩展方式与常见坑**。

---

## 1. 模块概述

RBAC 模块基于 **FastAPI + SQLAlchemy + MySQL + JWT(bcrypt)** 实现标准「用户-角色-权限」三层访问控制，并把鉴权统一收敛到**装饰器**方案（非 FastAPI `Depends`）。

做了什么：
- 五张核心表：`user` / `role` / `permission` + 关联表 `role_permission` / `user_role`
- JWT **只携带身份**（`sub` + `username`），权限每次请求查库 → **改权限即时生效，无需重新登录**
- 4 个内置角色：`super_admin` / `admin` / `teacher` / `student`
- 权限码采用 `资源:动作` 命名（如 `user:create`、`score:read`）
- 装饰器鉴权：`@auth_required` / `@require_role` / `@require_permission`
- `super_admin` 特殊保护（禁止被非超管操作、禁止删除最后一个、禁止非超管授予）
- 统一响应体 `{code, message, data}`，全局异常自动记录日志（见 `app/core/logger.py`）
- `seed_rbac.py` 一键初始化角色、权限与默认超管（幂等）

技术栈：
| 能力 | 选型 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0（`Mapped` / `select()`） |
| 数据库 | MySQL 8（PyMySQL 驱动） |
| 密码哈希 | bcrypt（`app.core.security.hash_password` / `verify_password`） |
| 令牌 | JWT（PyJWT，`HS256`） |
| 配置 | Pydantic Settings（`app.core.config`） |

---

## 2. 目录结构说明

```
学生管理系统与dify/
├── app/
│   ├── main.py                 应用入口：组装 app、注册路由/异常/日志、自动建表
│   ├── controllers/
│   │   ├── __init__.py         汇总各 router → controller_router
│   │   ├── auth.py             【鉴权接口】登录 / 注册 / 当前用户(/auth/me)
│   │   ├── users.py            【用户接口】增删改查 + 分配角色 (RBAC)
│   │   ├── roles.py            【角色接口】增删改查 + 分配权限 (RBAC)
│   │   ├── permissions.py      【权限接口】只读列表 (RBAC)
│   │   ├── deps.py             get_db / 分页参数等依赖
│   │   └── ...                 业务模块（class/student/teacher/score/employment/stats/gateway）
│   ├── services/
│   │   ├── user_service.py     【含 super_admin 保护】用户业务逻辑：认证/注册/密码哈希/角色分配
│   │   ├── role_service.py     角色业务逻辑：创建/删除守卫（禁止接口创建系统角色）
│   │   ├── permission_service.py / class_service.py / student_service.py / teacher_service.py
│   │   ├── score_service.py / employment_service.py / stats_service.py
│   │   └── __init__.py         导出各 *_service 单例
│   ├── repositories/
│   │   ├── user.py / role.py / permission.py / base.py  纯数据访问（CRUD / 查询）
│   │   └── __init__.py         导出各 *_repository 单例
│   ├── views/
│   │   ├── response.py         ApiResponse / success / error + 全局异常处理器
│   │   └── serializers.py      *_to_out（ORM → 响应 dict）
│   ├── core/
│   │   ├── config.py           全局配置（DB / JWT / 日志 / 管理员账号）
│   │   ├── database.py         SQLAlchemy 引擎 / SessionLocal / Base
│   │   ├── security.py         bcrypt + JWT 签发/校验（身份-only token）
│   │   ├── decorators.py       @auth_required / @require_role / @require_permission
│   │   ├── exceptions.py       业务异常（401/403/404/409/422...）
│   │   └── logger.py           统一日志（控制台 + 滚动文件）
│   ├── models/
│   │   ├── user.py             User 模型 + role_codes/permission_codes 聚合属性
│   │   ├── role.py             Role 模型 + 两张多对多关联表
│   │   ├── permission.py       Permission 模型
│   │   └── base.py             TimestampMixin（created_at/updated_at/is_deleted）
│   └── schemas/
│       ├── auth.py             LoginRequest / RegisterRequest / TokenResponse / *Out
│       └── rbac.py             RoleCreate/RoleOut/PermissionOut/UserRoleAssign/...
├── seed_rbac.py                初始化脚本：建表 + 角色/权限/默认超管（幂等）
├── .env                        （需自建）配置项见第 10 节
├── app/requirements.txt
└── logs/                       （运行时自动创建）滚动日志目录
```

**调用链**：`HTTP → controllers(Controller) → services(Service) → repositories(Repository) → models → MySQL → views 序列化 → {code,message,data}`。
鉴权旁路：`装饰器` 在路由执行前校验 Token + 权限，失败直接返回统一错误体，不进入业务逻辑。

---

## 3. 数据库表结构（5 张表）

> 每张业务表都带 `TimestampMixin` 注入的审计字段：`created_at`、`updated_at`、`is_deleted`（逻辑删除）。

### 3.1 `user`（用户表）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| user_id | INT | PK, 自增 | 用户主键 |
| username | VARCHAR(50) | NOT NULL, 索引 | 登录用户名（唯一） |
| password_hash | VARCHAR(128) | NOT NULL | bcrypt 哈希（**绝不存明文**） |
| is_active | BOOLEAN | NOT NULL, 默认 1 | 是否启用（禁用后无法登录） |
| email | VARCHAR(120) | 可空, 索引 | 邮箱（可选） |
| full_name | VARCHAR(50) | 可空 | 姓名/昵称（可选） |

> `email` / `full_name` 为本次新增可选字段。若数据库是**已有旧表**，请执行：
> `ALTER TABLE user ADD COLUMN email VARCHAR(120) NULL, ADD COLUMN full_name VARCHAR(50) NULL;`
> 或直接 `DROP` 该库后重新运行 `seed_rbac.py` 建表。

### 3.2 `role`（角色表）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| role_id | INT | PK, 自增 | 角色主键 |
| code | VARCHAR(50) | NOT NULL, 索引 | 角色编码（唯一，如 `super_admin`） |
| name | VARCHAR(50) | NOT NULL | 角色名称 |
| description | VARCHAR(200) | 可空 | 角色描述 |
| is_system | BOOLEAN | NOT NULL, 默认 0 | 是否系统角色（超级管理员：`is_system=1` 时权限校验直接放行） |

### 3.3 `permission`（权限表）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| permission_id | INT | PK, 自增 | 权限主键 |
| code | VARCHAR(100) | NOT NULL, 索引 | 权限码（`资源:动作`，如 `score:read`） |
| name | VARCHAR(100) | NOT NULL | 权限名称 |
| module | VARCHAR(50) | NOT NULL, 索引 | 所属模块（如 `score`） |
| description | VARCHAR(200) | 可空 | 权限描述 |

### 3.4 `role_permission`（角色↔权限 关联表）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| role_id | INT | PK, FK→role.role_id (CASCADE) | 角色 ID |
| permission_id | INT | PK, FK→permission.permission_id (CASCADE) | 权限 ID |

### 3.5 `user_role`（用户↔角色 关联表）
| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| user_id | INT | PK, FK→user.user_id (CASCADE) | 用户 ID |
| role_id | INT | PK, FK→role.role_id (CASCADE) | 角色 ID |

> 关联表均为 SQLAlchemy `Table` 对象，无独立 ORM 模型，仅承载多对多关系。

---

## 4. 权限点清单（共 44 个，按模块分组）

> 以 `seed_rbac.py` 中的 `PERMISSIONS` 为准。命名规则：`资源:动作`。

| 模块 | 权限码 | 名称 |
|---|---|---|
| **class** | `class:list` | 查询班级列表 |
| | `class:read` | 查看班级详情 |
| | `class:create` | 新增班级 |
| | `class:update` | 更新班级 |
| | `class:delete` | 删除班级 |
| | `class:restore` | 恢复班级 |
| **student** | `student:list` | 查询学生列表 |
| | `student:read` | 查看学生详情 |
| | `student:create` | 新增学生 |
| | `student:update` | 更新学生 |
| | `student:delete` | 删除学生 |
| | `student:restore` | 恢复学生 |
| **teacher** | `teacher:list` | 查询教师列表 |
| | `teacher:read` | 查看教师详情 |
| | `teacher:create` | 新增教师 |
| | `teacher:update` | 更新教师 |
| | `teacher:delete` | 删除教师 |
| | `teacher:restore` | 恢复教师 |
| **score** | `score:list` | 查询成绩列表 |
| | `score:read` | 查看成绩详情 |
| | `score:create` | 新增成绩 |
| | `score:update` | 更新成绩 |
| | `score:delete` | 删除成绩 |
| | `score:restore` | 恢复成绩 |
| **employment** | `employment:list` | 查询就业记录列表 |
| | `employment:read` | 查看就业记录详情 |
| | `employment:create` | 新增就业记录 |
| | `employment:update` | 更新就业记录 |
| | `employment:delete` | 删除就业记录 |
| | `employment:restore` | 恢复就业记录 |
| **stats** | `stats:view` | 查看统计分析 |
| **role** | `role:list` | 查询角色列表 |
| | `role:read` | 查看角色详情 |
| | `role:create` | 新增角色 |
| | `role:update` | 更新角色 |
| | `role:delete` | 删除角色 |
| | `role:assign-permission` | 分配角色权限 |
| **permission** | `permission:list` | 查询权限列表 |
| **user** | `user:list` | 查询用户列表 |
| | `user:read` | 查看用户详情 |
| | `user:create` | 新增用户 |
| | `user:update` | 更新用户 |
| | `user:delete` | 删除用户 |
| | `user:assign-role` | 分配用户角色 |

> 注：计划文档曾写「约 40 个」，实际 seed 初始化为 **44 个**（业务 5 模块各 6 个 = 30，加 stats/permission 各 1 = 32，加 role 6 / user 6 = 44）。以后新增权限点请同步改 `seed_rbac.py` 的 `PERMISSIONS`。

---

## 5. 角色-权限对照表（4 个角色）

| 角色 | code | 权限范围 | 超级管理员 |
|---|---|---|---|
| **超级管理员** | `super_admin` | 全部 **44** 个权限（所有模块读写） | ✅ `is_system=1`，权限校验直接放行 |
| **管理员** | `admin` | 除 `role:*`（6 个）外的全部 = **38** 个：业务 5 模块全量 + `stats:view` + `permission:list` + `user:*` | ❌ |
| **教师** | `teacher` | **15** 个：班级/学生/教师/就业 **只读** + 成绩全量 + `stats:view` | ❌ |
| **学生** | `student` | **11** 个：班级/学生/教师/成绩/就业 **只读** + `stats:view` | ❌ |

权限汇总规则：
- `super_admin`：拥有 `is_system` 角色 → **任何 `@require_permission` / `@require_role` 直接放行**（但仍需合法 Token）。
- `admin`：拥有除角色管理外的全部业务权限，可管理用户（含分配角色），但**不能创建/修改/删除角色与权限**。
- `teacher` / `student`：仅只读 + 各自可写域（教师可管成绩）。

---

## 6. 完整鉴权流程图

```
┌─────────────┐    POST /auth/register {username,password}     ┌──────────────┐
│  客户端     │ ─────────────────────────────────────────────▶ │  auth.register│
└─────────────┘                                              └──────┬───────┘
                                                                  │ 1. 不接收角色字段
                                                                  │ 2. create_user (bcrypt)
                                                                  │ 3. assign_roles(["student"])
                                                                  ▼
                                                        默认获得 student 角色
────────────────────────────────────────────────────────────────────────────
┌─────────────┐    POST /auth/login {username,password}        ┌──────────────┐
│  客户端     │ ─────────────────────────────────────────────▶ │  auth.login  │
└─────────────┘                                              └──────┬───────┘
                                                                  │ 1. authenticate (查库校验密码)
                                                                  │ 2. create_access_token(sub,username)
                                                                  │    → JWT 仅含身份，不含权限
                                                                  ▼
                                                          返回 { access_token,
                                                                 token_type:"bearer",
                                                                 expires_in:1800 }
────────────────────────────────────────────────────────────────────────────
┌─────────────┐   GET /users  Authorization: Bearer <token>    ┌──────────────┐
│  客户端     │ ─────────────────────────────────────────────▶ │ @require_perm│
│             │                                               │ ("user:list")│
│             │   ◀── 1. _extract_token(header)               │              │
│             │   ◀── 2. decode_token → 401 无效/过期          │              │
│             │   ◀── 3. get_with_roles(user_id) 查库加载      │              │
│             │            角色+权限(每次查库!)                 │              │
│             │   ◀── 4. _check_permission("user:list")        │              │
│             │            超管→放行 / 否则比对 permission_codes│              │
│             │   ◀── 不通过 → 403                             │              │
└─────────────┘   ◀── 通过 → 执行业务逻辑 → success({...})     └──────────────┘

调试入口：GET /auth/me  → 返回 { user_id, username, roles, permissions, is_super }
```

**关键点**：
- Token 里**没有权限**，权限在每次请求时按 DB 实时加载 → 改权限/角色后**立即生效，无需重新登录**。
- 所有鉴权失败统一返回 `{code,message,data:null}`，HTTP 状态码 = `code`（401/403/404/409…）。

---

## 7. 装饰器使用说明

位于 `app/core/decorators.py`，三个装饰器**都要求被装饰函数带 `request: Request` 参数**。

### 7.1 `@auth_required`
仅校验登录态（Bearer Token 合法且用户存在、已启用），不校验具体权限。成功后把用户对象挂到 `request.state.user`。

```python
from fastapi import Request
from app.core.decorators import auth_required
from app.views.response import ApiResponse, success
from app.views.serializers import user_to_out

@router.get("/me", response_model=ApiResponse[CurrentUserOut])
@auth_required
def me(request: Request):                      # 必须带 request: Request
    user = request.state.user                 # 当前登录用户（已加载角色+权限）
    return success(data=CurrentUserOut(
        user_id=user.user_id,
        username=user.username,
        roles=user.role_codes,
        permissions=sorted(user.permission_codes),
        is_super=any(r.is_system for r in user.roles),
    ).model_dump())
```

### 7.2 `@require_role("admin")`
在登录态基础上，**严格匹配角色码**（非超管也不会自动等于 admin）。

```python
@router.get("/admin-only")
@require_role("admin")              # 只有角色含 "admin" 的账号能进
def admin_only(request: Request):
    ...
```

### 7.3 `@require_permission("user:create")`
在登录态基础上按**权限码**校验。拥有 `is_system` 角色（超管）直接放行；否则校验该码是否在用户的 `permission_codes` 中。

```python
@router.post("/", response_model=ApiResponse[UserOut])
@require_permission("user:create")   # 缺权限 → 403
def create_user(request: Request, payload: UserCreate = Body(...), db: Session = Depends(get_db)):
    user = user_service.create_user(db, payload)
    return success(data=user_to_out(user), code=201)
```

> 装饰器同时兼容 `async def` 与 `def` 路由（内部自动选择 async/sync 包装器）。

---

## 8. 如何新增权限点 / 角色

### 8.1 新增一个权限点
1. 打开 `seed_rbac.py`，在 `PERMISSIONS` 对应模块下加一行：`("资源:动作", "名称")`。
   例：给 `score` 模块加导入权限：
   ```python
   "score": [
       ...
       ("score:import", "导入成绩"),   # 新增
   ],
   ```
2. 若要让某角色拥有它，在该角色 `permissions` 列表里加上 `"score:import"`（或直接用 `_codes("score")` 全量包含）。
3. 在业务路由上添加 `@require_permission("score:import")`。
4. 重新运行 `python seed_rbac.py`（幂等，会自动补建新权限并收敛角色映射）。

### 8.2 新增一个角色
**方式 A（推荐，代码内置）**：在 `seed_rbac.py` 的 `ROLES` 中追加一个字典（设 `is_system=False`，普通角色接口可创建/删除）。
**方式 B（运行时，仅普通角色）**：通过接口 `POST /roles`，但**接口禁止 `is_system=True`**（系统角色只能由 seed 创建）。

```bash
curl -X POST "http://127.0.0.1:8001/roles" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"auditor","name":"审计员","description":"只读审计","is_system":false}'
# 再 PUT /roles/{id}/permissions 绑定权限码
```

> 注意：角色/权限的增删改**仅管理员及以上**可操作（`role:*` 权限），且 `super_admin` 角色本身只能通过 seed 脚本生成，接口无法创建。

---

## 9. 常见坑

1. ❗ **被装饰函数必须带 `request: Request` 参数**。装饰器从 `request.headers["Authorization"]` 取 Token，并写入 `request.state.user`。缺了这个参数会运行时报错。即便函数体用不到 `request`，也要写上（仅登录/注册白名单接口除外）。
2. **JWT 只含身份，不含权限**。不要在前端依据 Token 里的信息判断权限（本项目 Token 里也没有权限字段）；权限以 `/auth/me` 返回或后端查库为准。
3. **改权限/角色后无需重新登录**。因为每次请求都查库。若你本地看到「改了还没生效」，多半是改错用户、或缓存了旧 Token——直接用 `/auth/me` 核对 `permissions`。
4. **注册接口不接收角色字段**。无论传什么角色参数都会被忽略，服务端强制绑 `student`。想建管理员请用 `seed_rbac.py`（默认超管）或超管通过 `/users/{id}/roles` 分配。
5. **`super_admin` 保护规则**：
   - 非超管不能操作（改/删）超管账号 → 403；
   - 只有超管能授予 `super_admin` 角色 → 否则 403；
   - 不能删除最后一个超管 → 409。
6. **`role:create` 接口禁止 `is_system=true`** → 否则 403。系统角色只能 seed 建。
7. **默认超管账号** `admin / admin123` 是 seed 写死的，**生产务必改密码**（改 `ADMIN_PASSWORD` 或登录后改）。
8. **`is_system` vs `is_super`**：`Role.is_system` 是角色属性；`/auth/me` 返回的 `is_super` 是「该用户是否拥有任一 is_system 角色」的派生布尔。
9. **日志**：所有 4xx/5xx 都会同时写控制台和 `logs/app.log`（滚动，10MB×5）。排查鉴权问题先看日志。
10. **已有数据库新增字段**：本次给 `user` 表加了 `email`/`full_name`，旧库需 `ALTER TABLE`（见第 3.1 节），否则注册会报列不存在。

---

## 10. 配置说明（.env）

在**项目根目录**放 `.env`（参考 `config.py` 默认值）。关键变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `APP_HOST` / `APP_PORT` | `0.0.0.0` / `8001` | 服务监听地址/端口 |
| `DEBUG` | `True` | 调试模式（True 时 SQLAlchemy `echo` 打印 SQL） |
| `DATABASE_URL` | 空 | 若提供则优先作为连接串 |
| `DB_HOST` / `DB_PORT` | `127.0.0.1` / `3306` | MySQL 地址 |
| `DB_USER` / `DB_PASSWORD` | `root` / `123456` | MySQL 账号 |
| `DB_NAME` | `student_management` | 数据库名 |
| `SECRET_KEY` | `change-me-in-production` | **JWT 签名密钥，生产必须改** |
| `ALGORITHM` | `HS256` | JWT 算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | access_token 有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `10080` | 已定义（refresh_token 生成函数使用）；登录接口当前仅签发 access_token（7 天） |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | seed 默认超管账号（生产必改） |
| `CORS_ORIGINS` | `*` | 允许跨域来源（逗号分隔；`*` 表示全部） |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `10` / `100` | 分页默认/最大页大小 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `LOG_DIR` / `LOG_FILE` | `logs` / `app.log` | 日志目录（项目根）/文件名 |
| `LOG_BACKUP_COUNT` / `LOG_MAX_BYTES` | `5` / `10485760` | 滚动备份数 / 单文件上限（10MB） |

> 完整变量以 `app/core/config.py` 的 `Settings` 类为准。

---

## 11. 接口清单速查

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/auth/login` | 公开 | 登录取 Token |
| POST | `/auth/register` | 公开 | 注册（默认 `student`） |
| GET | `/auth/me` | 登录 | 当前用户信息（调试入口） |
| GET | `/users` | `user:list` | 用户列表 |
| GET | `/users/{id}` | `user:read` | 用户详情 |
| POST | `/users` | `user:create` | 新增用户 |
| PUT | `/users/{id}` | `user:update` | 更新用户 |
| DELETE | `/users/{id}` | `user:delete` | 删除用户 |
| PUT | `/users/{id}/roles` | `user:assign-role` | 分配/重设角色 |
| GET | `/roles` | `role:list` | 角色列表 |
| GET | `/roles/{id}` | `role:read` | 角色详情 |
| POST | `/roles` | `role:create` | 新增角色（禁 `is_system`） |
| PUT | `/roles/{id}` | `role:update` | 更新角色 |
| DELETE | `/roles/{id}` | `role:delete` | 删除角色 |
| PUT | `/roles/{id}/permissions` | `role:assign-permission` | 分配权限 |
| GET | `/permissions` | `permission:list` | 权限列表（只读） |
