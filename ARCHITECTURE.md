# 架构说明

## 整体架构

项目采用 **MVC + Service / Repository** 分层架构（在 MVC 基础上进一步把业务逻辑与纯数据访问拆出来），代码按职责分目录：

| 层 | 目录 | 一句话职责 |
|---|---|---|
| Controller | `app/controllers/` | 把请求接进来、调用 Service、拼装响应还回去 |
| Service | `app/services/` | 业务逻辑：密码哈希、RBAC 守卫、校验、编排 Repository |
| Repository | `app/repositories/` | 纯数据访问（CRUD / 查询），不含业务规则 |
| View | `app/views/` + `app/schemas/` | 响应体拼装（`*_to_out`）与统一响应结构 / 出入参 Schema |
| Model | `app/models/` | SQLAlchemy ORM 表结构 |
| core | `app/core/`（横切） | 配置、数据库、安全、鉴权装饰器、日志、异常、转发 |

一个关键取舍：**业务逻辑不放 Controller，也不下沉到 Repository**。`controllers/` 只做路由与编排，`repositories/` 只做数据读写，**所有业务规则（哈希、RBAC 守卫、唯一性/外键校验、删除保护）集中在 `services/`**，从而保证业务可被复用、可被单测，且不污染数据层。

## 各层职责

### Controller —— 调度（薄）

`controllers/` 下的路由函数只允许出现：装饰器（含权限声明）、参数声明、一次 `service` 调用、`views.serializers.*_to_out` 拼装 + `success(...)` 包装。不含 SQL，不含业务规则。

```python
@router.post("/", status_code=201, response_model=ApiResponse[StudentOut], summary="新增学生")
@require_permission("student:create")
def create_student(request: Request, payload: StudentCreate = Body(...), db: Session = Depends(get_db)):
    student = student_service.create_student(db, payload, operator=request.state.user)
    return success(data=student_to_out(student), message="学生创建成功", code=201)
```

依赖在 `controllers/deps.py` 统一管理：`get_db()` 提供请求级数据库会话，`PaginationParams` 解析并兜底分页参数。

鉴权通过装饰器（`app/core/decorators.py`）而非 FastAPI `Depends`：`@auth_required` / `@require_role` / `@require_permission`；被装饰函数必须带 `request: Request` 参数（装饰器从中取 Token 并写入 `request.state.user`）。

### Service —— 业务逻辑（胖）

`services/` 承载所有"换个接口也得这么做"的逻辑：

- 密码哈希（`bcrypt`）、登录认证、注册时绑定学生；
- RBAC 守卫：最后一个超级管理员保护、授予 `super_admin` 的限制、接口禁止创建 `is_system=True` 系统角色；
- 业务校验：外键存在性（如学生→班级）、唯一性、删除前的关联保护（如班级下还有学生时禁止删除）；
- 编排一个或多个 `repositories` 完成持久化，必要时组合多次读写于同一事务。

### Repository —— 纯数据访问（瘦）

`repositories/` 只做对表的 CRUD 与查询，不含业务规则。

- `repositories/base.py`：泛型 `RepositoryBase`，封装分页 + 模糊搜索、按主键查询、局部更新、逻辑删除与恢复、`unique_specs` 唯一性校验（重复创建 / 改名撞车 / 恢复后重名，均抛 409）。所有查询默认过滤 `is_deleted == False`。
- `repositories/<实体>.py`：该实体独有的查询/写入，例如成绩查询时预加载关联实体——**业务字段拼装（如给成绩补 `student_name`）已由 View 层负责，不在此处**。

### View —— 返回格式

- `views/serializers.py`：`*_to_out(orm) -> dict`，把 ORM 对象转成接口响应字典（集中管理，避免在各地散落拼装）。
- `views/response.py`：统一响应体 `ApiResponse[T]` 与全局异常处理器（`BusinessException` / `HTTPException` / 422 / 500 统一转成 `{code, message, data}`）。
- `schemas/`：Pydantic 模型。`*Out` 定义响应结构（通过 `response_model=ApiResponse[X]` 生效，FastAPI 会按它序列化并过滤字段）；`*Create` / `*Update` 负责入参校验。

### Model —— 表结构

`models/` 定义 ORM。`base.py` 的 `TimestampMixin` 给每张表统一注入 `created_at`、`updated_at`、`is_deleted`；`role.py` 中定义 `user_role`、`role_permission` 两张多对多关联表。

### core —— 横切基础设施

`core/` 不属于 MVC 任意一层，被各层共用：

- `config.py`：读取 `.env`（`pydantic-settings`，带类型校验与默认值）
- `database.py`：引擎、会话工厂、`DeclarativeBase`
- `security.py`：密码哈希（`bcrypt`）+ JWT 编解码（`PyJWT`）
- `decorators.py`：RBAC 鉴权装饰器
- `logger.py`：日志初始化（`RotatingFileHandler`，10MB / 5 备份）
- `exceptions.py`：业务异常体系（`NotFoundException` / `DuplicateException` / `ConflictException` / `UnauthorizedException` / `ForbiddenException` 等）
- `forwarder.py`：Dify `/gateway` 自转发逻辑（与数据库无关）

## 层与层之间的调用关系

```
        ┌──────────────┐
        │  HTTP 请求   │
        └──────┬───────┘
               ▼
┌──────────────────────────────────┐
│ Controller      app/controllers/ │   ① 解析参数、注入 Session、鉴权装饰器
└──────────────┬───────────────────┘
               │ ② service.method(db, payload, operator)
               ▼
┌──────────────────────────────────┐
│ Service        app/services/     │   ③ 业务规则 + 校验 + 编排
└──────────────┬───────────────────┘
               │ ④ repository.method(db, ...)
               ▼
┌──────────────────────────────────┐
│ Repository    app/repositories/  │   ⑤ 纯数据读写（ORM → SQL）
│               app/models/        │
└──────────────┬───────────────────┘
               ▼
           ┌────────┐
           │ MySQL  │
           └────────┘
               │ ⑥ 返回后逐层上溯
               ▼
┌──────────────────────────────────┐
│ View           app/views/        │   ⑦ serializers.*_to_out + ApiResponse
└──────────────┬───────────────────┘
               ▼
        ┌──────────────┐
        │ {code,       │
        │  message,    │
        │  data}       │
        └──────────────┘
```

规则：

- Controller **只向下调用** Service，Service 只向下调用 Repository，Model / Repository 不知道 HTTP 的存在。
- View 不参与调用链，它是挂在 Controller 出口上的**声明 + 拼装**，由 FastAPI 在序列化阶段执行。
- 层内依赖方向由下往上不允许：`repositories/` 可依赖 `models/`；`services/` 可依赖 `repositories/` 与 `models/`；`controllers/` 可依赖 `services/` / `views/` / `schemas/`；反向依赖一律禁止。

### 异常路径（旁路）

业务失败由 Service / Repository 抛业务异常，全局处理器统一转成响应体：

```
service / repository 内 raise NotFoundException / DuplicateException / ConflictException / ForbiddenException
        │
        ▼
views/response.py 的全局异常处理器（BusinessException / HTTPException / 422 / 500）
        │
        ▼
统一错误体 { "code": 404, "message": "...", "data": null }
```

好处：错误格式只有一处定义，Controller 里看不到 `try/except`。

## 鉴权设计（JWT + RBAC）

- `access_token` **仅存放身份信息**（`sub`=用户 ID、`username`、签发时间、过期时间），**不携带角色/权限**。
- 鉴权装饰器每次都按 `sub` 从数据库重新加载用户角色与权限，因此修改权限/角色后**即时生效，无需重新登录**。
- `refresh_token` 的生成函数（`security.create_refresh_token`）已就绪，但登录接口当前仅签发 `access_token`，刷新流程待后续迭代接入。
- 失败响应同样走统一格式：`401`（未携带/无效 Token）、`403`（Token 有效但权限不足）。

详细权限码、角色与接口清单见 [RBAC_USAGE.md](RBAC_USAGE.md)。

## 目录与分层的对应

```
app/
├── main.py              应用入口：组装 FastAPI、注册中间件/异常处理器/路由
├── controllers/         Controller 层 —— 路由函数（薄）
│   ├── deps.py          依赖注入（数据库会话、分页参数）
│   ├── class_.py student.py teacher.py score.py employment.py
│   ├── auth.py users.py roles.py permissions.py stats.py
│   └── gateway.py       Dify 转发入口
├── services/            Service 层 —— 业务逻辑（胖）
│   └── *_service.py     user / role / permission / class_ / student / teacher / score / employment / stats
├── repositories/        Repository 层 —— 纯数据访问（瘦）
│   ├── base.py          RepositoryBase（分页、模糊搜索、唯一性校验、逻辑删除/恢复）
│   └── *_repository.py  各实体的 CRUD / 查询
├── views/               View 层 —— 响应拼装与统一响应
│   ├── serializers.py   *_to_out（ORM → dict）
│   └── response.py      ApiResponse[T] + 全局异常处理器
├── models/              Model 层 —— ORM 表结构
├── schemas/             入参校验与出参结构（Pydantic）
└── core/               基础设施（横切，被各层共用）
    ├── config.py        环境变量与全局配置
    ├── database.py      引擎、会话工厂、DeclarativeBase
    ├── security.py      密码哈希 + JWT 编解码
    ├── decorators.py    RBAC 鉴权装饰器
    ├── logger.py        日志初始化
    ├── exceptions.py    业务异常体系
    └── forwarder.py     自转发逻辑
```

`core/` 是横切关注点：配置、连接、异常、日志不属于业务，因此单独成目录，各层都可依赖它，它不依赖任何一层。

## 技术选型理由

**FastAPI** —— 直接由类型注解生成 OpenAPI 文档，`/docs` 开箱可用；依赖注入（`Depends`）天然适配"每个请求一个数据库会话"；原生基于 Pydantic，让 View 层可以用声明代替序列化代码。

**SQLAlchemy 2.0** —— ORM 把表结构与 Python 类绑定；`Mapped` 类型注解能在 IDE 里补全字段名，配合 `select()` 新风格写出可组合查询。会话与事务边界清晰（`sessionmaker` 交给 `get_db()` 管理），逻辑删除只需在基类查询里加一个过滤条件，而 `unique_specs` 这类跨表规则也能在 Repository 基类里一次实现、多实体复用。

**Pydantic v2** —— 入参校验和出参契约用同一套模型语言表达；`response_model` 会在返回前过滤未声明字段并做类型转换，把 View 层契约真正**落到运行时**。`pydantic-settings` 则让 `.env` 读取带类型校验和默认值，配置项写错在启动时就会报错。

**PyJWT + bcrypt** —— Token 只存身份、权限每次查库，兼顾无状态与"权限即时生效"；bcrypt 自带盐，密码哈希不可逆。

**MySQL** —— 五张表之间是典型的强关系型结构（学生→班级、成绩→学生+教师、就业→学生），外键与聚合统计（`/stats/*`）都是关系库的强项。

**httpx** —— `/gateway` 需要异步发起 HTTP 请求，与 FastAPI 的异步模型一致，避免在协程里用同步客户端阻塞事件循环。
