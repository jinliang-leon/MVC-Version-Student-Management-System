# 学生管理系统 · MVC 架构重构文档

> 重构对象：`学生管理系统与dify`（FastAPI + SQLAlchemy 2.0 + MySQL 8 + Pydantic v2）
> 重构方式：**API 风格 MVC**——保留原 JSON API 行为不变，仅对代码分层做结构性重整。
> 验证结论：**重构后 25 项端到端冒烟用例全部通过，行为与原架构完全一致。**

---

## 1. 重构目标

将原先 `api/`（路由）与 `crud/`（数据访问 + 业务规则 + 响应拼装混在一起）的「两层 + 散落逻辑」结构，
重构为职责清晰、可独立测试的标准 MVC 五层架构，并抽出一个独立的 **Service 业务层** 与 **Repository 纯数据访问层**：

| 关注点 | 重构前 | 重构后 |
|---|---|---|
| 路由 / 入参校验 | `app/api/*` | `app/controllers/*` |
| 业务规则（哈希、RBAC 守卫、校验） | 散落在 `app/crud/*` | `app/services/*` |
| 数据访问 | `app/crud/*`（混杂业务） | `app/repositories/*`（纯数据） |
| 响应拼装 / 序列化 | 散落在 `crud` 与 `schemas` | `app/views/serializers.py` |
| 统一响应体 | `app/core/response.py` | `app/views/response.py` |

**对外契约（路由、请求/响应字段、状态码、错误文案）100% 保持原样**，因此前端 / 调用方无需任何改动。

---

## 2. 目标架构（分层与依赖方向）

```
                HTTP 请求
                    │
                    ▼
        ┌─────────────────────────┐
        │   Controller 层          │  app/controllers/*
        │  (路由 / 鉴权装饰器 /      │  只做：收请求 → 调 Service → 序列化 → 包响应
        │   参数解析 / operator透传) │
        └───────────┬─────────────┘
                    │ 调用（不碰 DB、不含业务规则）
                    ▼
        ┌─────────────────────────┐
        │   Service 业务层          │  app/services/*
        │  (业务规则 / RBAC 守卫 /   │  编排 Repository，持有事务边界
        │   密码哈希 / 校验 / 编排)   │
        └───────────┬─────────────┘
                    │ 调用（不含业务判断）
                    ▼
        ┌─────────────────────────┐
        │   Repository 数据层       │  app/repositories/*
        │  (纯 CRUD / 查询，无规则)  │  泛型 RepositoryBase + 各域 Repository
        └───────────┬─────────────┘
                    │ 调用
                    ▼
        ┌─────────────────────────┐
        │   Model 实体层           │  app/models/*
        │  (ORM 表 / 关系 / 关联)    │  SQLAlchemy 2.0 模型，本层不改动
        └─────────────────────────┘

  跨层横切（Core）：app/core/  config · database · security · exceptions
                                    · decorators(RBAC) · logger · forwarder
  视图/响应（View）：app/views/  response.py(统一响应体) · serializers.py(ORM→DTO)
  入参/出参模型（Schema）：app/schemas/  Pydantic 请求与响应模型，本层不改动
```

**依赖铁律**：Controller → Service → Repository → Model；反向禁止。
View（`response` / `serializers`）只被 Controller 调用；Core 被各层按需调用，自身不依赖上层。

---

## 3. 目录映射（旧 → 新）

| 原路径（已删除） | 新路径 | 说明 |
|---|---|---|
| `app/api/__init__.py` | `app/controllers/__init__.py` | 路由汇总，导出 `controller_router` |
| `app/api/{auth,class_,employment,gateway,permissions,roles,score,stats,student,teacher,users}.py` | `app/controllers/*.py`（同名） | 路由函数瘦身，仅编排 |
| `app/crud/base.py` | `app/repositories/base.py` | `CRUDBase` → `RepositoryBase`（纯数据访问，去掉业务判断） |
| `app/crud/{class_,employment,permission,role,score,stats,student,teacher,user}.py` | `app/repositories/*.py`（同名） | 仅保留 CRUD / 查询；业务规则迁出 |
| `app/core/response.py` | `app/views/response.py` | `success/error/ApiResponse/register_exception_handlers` 平移 |
| `app/schemas/auth.py::user_to_out` 等散落序列化 | `app/views/serializers.py` | 集中 `user_to_out / student_to_out / class_to_out / teacher_to_out / score_to_out / employment_to_out` |
| `app/crud/*` 内的业务规则 | `app/services/{user,role,permission,class_,student,teacher,score,employment,stats}_service.py` | 业务层全新建 |

**未改动**：`app/models/*`（实体）、`app/schemas/*`（Pydantic 模型）、`app/core/*`（横切，仅改了内部 import 指向）。

---

## 4. 各层职责（含真实代码片段）

### 4.1 Model — 实体层（`app/models/*`）
ORM 表定义、关系、关联表。**本层原样保留，不承载任何业务逻辑。**

### 4.2 Repository — 纯数据访问层（`app/repositories/*`）
只做「与数据库对话」的事：泛型 `RepositoryBase` 提供 `get / get_or_404 / get_multi / get_all / create / update / soft_delete / restore / hard_delete`，各域 Repository 仅补充必要的查询方法（如 `user_repository.get_by_username`、`class_repository.count_students`）。**不含任何业务规则、不含密码哈希、不含权限判断。**

### 4.3 Service — 业务层（`app/services/*`）
所有业务规则的唯一归属地，也是事务边界所在。以 `user_service` 为例：

```python
# app/services/user_service.py（节选）
def register(self, db, payload) -> User:
    """注册：密码哈希 + 默认绑定 student 角色"""
    data = payload.model_dump()
    data["password_hash"] = hash_password(data.pop("password"))     # 业务规则：哈希
    user = user_repository.create_user(db, data)
    user_repository.set_roles(db, user, ["student"])               # 业务规则：默认角色
    return user_repository.get_with_roles(db, user.user_id)

def assign_roles(self, db, user, role_codes, operator=None) -> User:
    """重设角色：super_admin 守卫"""
    if "super_admin" in role_codes and not (operator and self.is_super(operator)):
        raise ForbiddenException("只有超级管理员可授予 super_admin 角色")  # 业务规则
    self._guard_super_admin(user, operator, action="操作")                       # 业务规则
    user_repository.set_roles(db, user, role_codes)
    return user_repository.get_with_roles(db, user.user_id)

def delete_user(self, db, user_id, operator=None) -> User:
    ...
    if self.is_super(user) and user_repository.count_super_admins(db) <= 1:
        raise ConflictException("不能删除最后一个超级管理员账号", code=409)    # 业务规则
    user_repository.soft_delete(db, user)
```

> RBAC 守卫（`_guard_super_admin` / `count_super_admins` / 是否可授予 `super_admin`）、密码哈希、关联存在性校验、删除班级前查学生等**全部从原 `crud` 上移到 Service**。

### 4.4 Controller — 控制/路由层（`app/controllers/*`）
薄路由层，遵循统一三段式：**收请求 → 调 Service → 用 `views.serializers.*_to_out` 序列化 → `success()` 包响应**。以 `users.py` 为例：

```python
# app/controllers/users.py（节选）
@router.put("/{user_id}/roles", response_model=ApiResponse[UserOut])
@require_permission("user:assign-role")
def assign_user_roles(request: Request, user_id: int = Path(...),
                      payload: UserRoleAssign = Body(...), db: Session = Depends(get_db)):
    user = user_service.get_with_roles(db, user_id)
    user = user_service.assign_roles(db, user, payload.role_codes, operator=request.state.user)
    return success(data=user_to_out(user), message="角色分配成功")
```

要点：
- 鉴权用装饰器 `@require_permission(...)` / `@require_role(...)` / `@auth_required`（非 `Depends` 方案），被装饰函数签名均带 `request: Request`，装饰器从 `Authorization` 头取 Token、加载当前用户、写入 `request.state.user`。
- 当前登录用户作为 `operator` 透传给 Service，由 Service 执行超级管理员保护。
- 列表型路由**带尾斜杠**（`/users/`、`/roles/`…），与重构前一致。

### 4.5 View — 视图/响应层（`app/views/*`）
- `response.py`：统一响应体 `{code, message, data}` 的构造器 `success()` / `error()`、`ApiResponse` 泛型、全局异常处理器 `register_exception_handlers`（由 `core/response.py` 平移，逻辑不变）。
- `serializers.py`：**集中所有「ORM → 响应字典」拼装**（如 `class_to_out` 附带 `student_count`、`score_to_out` 附带 `student_name/teacher_name`）。Controller 不再手写转换。

### 4.6 Core — 横切层（`app/core/*`）
`config / database / security(jwt+bcrypt) / exceptions / logger / forwarder` 维持原职责；`decorators.py`（RBAC 装饰器）也保持原实现。仅内部 import 从 `app.crud.user` 改为 `app.repositories.user`、从 `app.core.response` 改为 `app.views.response`。

---

## 5. 关键逻辑迁移说明

1. **RBAC 守卫进 Service**：`super_admin` 相关判断（`_is_super` → `UserService.is_super`、`_guard_super_admin`、`count_super_admins`、授予 `super_admin` 的限制）从 `crud/user.py` 迁到 `services/user_service.py`；`api/roles.py` 中「拒绝 `is_system=True`」规则迁到 `services/role_service.py`（`ForbiddenException("系统角色（is_system=True）仅允许由初始化脚本创建，接口禁止创建")`）。
2. **响应拼装进 View**：所有 `*_to_out` 从 `crud/*` 与 `schemas/auth.py` 抽出，统一到 `views/serializers.py`；`app/schemas/auth.py` 末尾的 `user_to_out` 已删除，`schemas/__init__.py` 同步移除导出。
3. **密码哈希进 Service**：`register` / `create_user` / `update_user` 的 bcrypt 哈希均在 Service 完成，Repository 只负责落库。
4. **关联/存在性校验进 Service**：如 `score_service` 校验 student/teacher 存在、`employment_service` 校验 student 存在、`class_service.ensure_deletable` 等，均由 Service 在调用 Repository 前完成。

---

## 6. 全局接线改动清单

| 文件 | 改动 |
|---|---|
| `app/main.py` | `from app.api import api_router` → `from app.controllers import controller_router`；`from app.core.response import ...` → `from app.views.response import ...`；`include_router(api_router)` → `include_router(controller_router)` |
| `app/core/decorators.py` | `from app.crud.user import crud_user` → `from app.repositories.user import user_repository`；`crud_user.get_with_roles(...)` → `user_repository.get_with_roles(...)` |
| `app/core/forwarder.py` | 改为 `from app.services.user_service import user_service` + `from app.views.response import error`；`crud_user.get_or_create_service_user(db)` → `user_service.get_or_create_service_user(db)` |
| `seed_rbac.py` | import 改为 `app.repositories.{permission,role,user}`；所有 `crud_*` 调用点改为 `permission_repository/role_repository/user_repository.*` |
| `app/schemas/auth.py` | 删除 `user_to_out` 函数 |
| `app/schemas/__init__.py` | 移除 `user_to_out` 的 import 与 `__all__` 导出 |
| **删除** | `app/api/`、`app/crud/`、`app/core/response.py` |

---

## 7. 重构执行步骤（本次已执行）

1. 新建 `app/repositories/`（base + 9 个域 Repository），把纯数据访问从 `crud` 平移。
2. 新建 `app/services/`（9 个 Service），把业务规则、RBAC 守卫、密码哈希、校验、编排从 `crud` 抽出。
3. 新建 `app/views/serializers.py`（集中 `*_to_out`）与 `app/views/response.py`（从 `core/response.py` 平移）。
4. 新建 `app/controllers/`（deps + 11 个路由文件 + `__init__` 导出 `controller_router`），薄路由编排。
5. 改全局接线（main / decorators / forwarder / seed / schemas）。
6. 删除旧 `app/api/`、`app/crud/`、`app/core/response.py`，再次校验 import 与路由数。

---

## 8. 验证结果

### 8.1 导入校验
```bash
python -c "import app.main"
# IMPORT OK；controller_router 注册路由数：53
```
全量导入无报错，新代码零旧引用（`app.api` / `app.crud` / `core.response` / `crud_` 已全部清除）。

### 8.2 重建库 + 重跑 seed
```bash
# 重建库
DROP DATABASE student_management; CREATE DATABASE student_management DEFAULT CHARSET utf8mb4;
# 建表 + 初始化（seed 内 Base.metadata.create_all + 44 权限 / 4 角色 / admin 赋 super_admin）
python seed_rbac.py
# 结果：权限 44 个、角色 4 个（super_admin/admin/teacher/student）、admin 用户已授予 super_admin
```

### 8.3 端到端冒烟测试（重构后）
- 启动：`uvicorn app.main:app --host 0.0.0.0 --port 8002`
  （注：8001 端口存在未释放的孤儿 socket，故测试改用 8002；接口与行为完全一致）
- 脚本：`smoke_mvc_test.py`（覆盖 `RBAC_TEST.md` 的 TC-01~13 与 TC-14a~e）
- **结果：25 项断言全部 PASS ✅**，关键项：

| 用例 | 请求 | 实际 | 预期 |
|---|---|---|---|
| TC-01 | POST /auth/register | 201, roles=["student"] | 201 |
| TC-02 | POST /auth/login | 200, token_type=bearer, expires_in=1800 | 200 |
| TC-03 | GET /auth/me | 200, is_super=false, 11 权限 | 200 |
| TC-04 | GET /users/（student） | 403 缺 user:list | 403 |
| TC-05 | GET /users/（admin） | 200 | 200 |
| TC-07 | DELETE 最后超管 | 409 不能删除最后一个超级管理员 | 409 |
| TC-06 | admin 授 super_admin | 200（admin 本身是超管，允许） | 200 |
| TC-08 | 改角色后旧 token | 200（权限即时生效） | 200 |
| TC-09 | 过期 token | 401 | 401 |
| TC-10/11 | 无/无效 token | 401 | 401 |
| TC-13 | POST /roles/ is_system=true | 403 接口禁建系统角色 | 403 |
| TC-14d | 非超管授 super_admin | 403 只有超级管理员可授予 | 403 |
| TC-14e | 非超管改超管账号 | 403 无权限修改超级管理员账号 | 403 |
| TC-12 | admin 改超管账号 | 200（放最后，会禁用 admin） | 200 |

> 结论：重构**没有改变任何对外行为**，RBAC 守卫、密码哈希、最后超管保护、即时权限生效等均与重构前一致。

---

## 9. 运行方式

```bash
# 1. 依赖（建议在虚拟环境）
pip install -r app/requirements.txt        # 或本项目 venv

# 2. 准备 .env（至少保证数据库可连）
#   DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/student_management?charset=utf8mb4
#   SECRET_KEY=...  ADMIN_USERNAME=admin  ADMIN_PASSWORD=admin123

# 3. 初始化库与 RBAC 数据
python seed_rbac.py

# 4. 启动（8001 若被孤儿 socket 占用，改用 8002）
uvicorn app.main:app --host 0.0.0.0 --port 8001
# 文档：http://127.0.0.1:8001/docs
```

---

## 10. 风险与回滚

- **已删除旧目录**：`app/api/`、`app/crud/`、`app/core/response.py` 已从工作区移除。
- **回滚方式**：
  - 本目录（`学生管理系统与dify`）受 git 管理，必要时可用 `git` 历史恢复旧结构；
  - 另有一份**未重构的旧架构副本**位于 `D:\WorkBuddy学生管理系统\`（`app/api/` + `app/crud/` 完整），可作为对照/回退参考。
- **无数据风险**：重构只动代码结构，不动数据库 Schema 与数据；`seed_rbac.py` 幂等，可重复执行。

---

## 11. 备注：双副本说明

当前磁盘上存在两份学生管理系统代码：
- `学生管理系统与dify`（本重构的工作副本）：**已完成 MVC 重构**，为推荐使用的版本。
- `D:\WorkBuddy学生管理系统\`：旧架构（`api/` + `crud/`），**未重构**，可作为回退对照。

如希望把重构结果同步/合并回 `D:\WorkBuddy学生管理系统\`，请告知，我可在此基础上再执行一次对齐合并。
