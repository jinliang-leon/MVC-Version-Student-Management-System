# 架构说明

## 整体架构

项目采用 **MVC 三层架构**，代码按职责分目录，而不是按功能堆在一起：

| 层 | 目录 | 一句话职责 |
|---|---|---|
| Model | `app/models/`、`app/crud/` | 数据从哪来、业务规则怎么定 |
| View | `app/schemas/` | 接口返回什么格式 |
| Controller | `app/api/` | 把请求接进来、把结果还回去 |

一个刻意的取舍：**不设 `services/` 层**。业务规则全部下沉到 `crud/`（即"胖 Model"），因此 Controller 只剩路由声明，没有任何可复用的业务代码被拆成薄薄一层中转。

## 各层职责

### Model —— 数据 + 业务逻辑

`models/` 定义表结构，`crud/` 承载对表的全部操作与规则。

- `models/base.py`：`TimestampMixin` 给每张表统一注入 `created_at`、`updated_at`、`is_deleted` 三个审计字段；主键命名各表自定义（`class_id`、`student_id`、……）。
- `models/*.py`：5 张表的 ORM 定义 —— `class`、`student`、`teacher`、`score`、`employment`。
- `crud/base.py`：泛型 `CRUDBase`，封装分页 + 模糊搜索、按主键查询、局部更新、逻辑删除与恢复、`unique_specs` 唯一性校验（重复创建 / 改名撞车 / 恢复后重名，均抛 409）。所有查询默认过滤 `is_deleted == False`。
- `crud/<实体>.py`：该实体独有的规则。例如学生创建前校验班级是否存在（外键预校验）、成绩/就业记录拼装 `student_name`、班级删除前确认班里没有学生。

判定标准：**凡是"换个接口也得这么做"的逻辑，都属于这一层。**

### View —— 返回格式

`schemas/` 用 Pydantic 模型描述接口的输入输出结构。

- `*Out`：响应结构。通过路由装饰器上的 `response_model=ApiResponse[StudentOut]` 生效，FastAPI 会按它序列化并过滤字段——**不在这份契约里的字段不会泄漏出去**。
- `*Create` / `*Update`：入参校验（必填项、长度、取值枚举等），请求体不合法直接 422。
- `common.py`：`PageResult[T]` 分页结果、`PageParams` 分页参数。
- `validators.py`：跨 Schema 复用的自定义校验。

绑定方式是**声明式**的：View 不写序列化代码，只声明结构，落点在 Controller 的装饰器上。

### Controller —— 调度

`api/` 下的路由函数只允许出现四样东西：装饰器（含 `response_model`）、参数声明、一次 `crud` 调用、`success(...)` 包装。

```python
@router.post("/", status_code=201, response_model=ApiResponse[StudentOut], summary="新增学生")
def create_student(payload: StudentCreate = Body(...), db: Session = Depends(get_db)):
    return success(data=crud_student.create_student(db, payload), message="学生创建成功", code=201)
```

依赖在 `api/deps.py` 统一管理：`get_db()` 提供请求级数据库会话，`PaginationParams` 解析并兜底分页参数。

## 层与层之间的调用关系

```
        ┌──────────────┐
        │  HTTP 请求   │
        └──────┬───────┘
               ▼
┌──────────────────────────────────┐
│ Controller        app/api/       │   ① 解析参数、注入 Session
│ 路由函数                          │
└──────────────┬───────────────────┘
               │ ② crud_xxx.method(db, payload)
               ▼
┌──────────────────────────────────┐
│ Model             app/crud/      │   ③ 业务规则 + 事务
│                   app/models/    │      （ORM → SQL）
└──────────────┬───────────────────┘
               ▼
           ┌────────┐
           │ MySQL  │
           └────┬───┘
               │ ④ 返回 ORM 对象 / dict
               ▼
┌──────────────────────────────────┐
│ View              app/schemas/   │   ⑤ response_model 序列化 + 校验
└──────────────┬───────────────────┘
               ▼
        ┌──────────────┐
        │ {code,       │
        │  message,    │
        │  data}       │
        └──────────────┘
```

规则：

- Controller **只向下调用** Model，不反向；Model 不知道 HTTP 的存在。
- View 不参与调用链，它是挂在 Controller 出口上的**声明**，由 FastAPI 在序列化阶段执行。
- 层内依赖方向由下往上不允许：`crud/` 可以依赖 `models/` 和 `schemas/`，`api/` 可以依赖两者，反向依赖一律禁止。

### 异常路径（旁路）

业务失败不靠 Controller 逐层判断，而是由 Model 抛业务异常，全局处理器统一转成响应体：

```
crud 内 raise NotFoundException / DuplicateException / ConflictException
        │
        ▼
core/response.py 的全局异常处理器（BusinessException / HTTPException / 422 / 500）
        │
        ▼
统一错误体 { "code": 404, "message": "...", "data": null }
```

好处：错误格式只有一处定义，Controller 里看不到 `try/except`。

## 目录与分层的对应

```
app/
├── main.py          应用入口：组装 FastAPI、注册中间件/异常处理器/路由
├── api/             Controller 层 —— 路由函数
│   ├── deps.py      依赖注入（数据库会话、分页参数）
│   ├── class_.py student.py teacher.py score.py employment.py
│   ├── stats.py     6 个统计接口
│   └── gateway.py   Dify 转发入口
├── models/          Model 层 —— ORM 表结构
├── crud/            Model 层 —— 数据访问与业务规则
├── schemas/         View 层 —— 入参校验与出参结构
└── core/            基础设施（不属于 MVC 任意一层，被各层共用）
    ├── config.py    环境变量与全局配置
    ├── database.py  引擎、会话工厂、DeclarativeBase
    ├── response.py  统一响应体 ApiResponse[T] + 全局异常处理器
    ├── exceptions.py 业务异常体系
    └── forwarder.py 自转发逻辑（与数据库无关，故不放 crud/）
```

`core/` 是横切关注点：配置、连接、异常、日志不属于业务，因此单独成目录，三层都可依赖它，它不依赖任何一层。

## 技术选型理由

**FastAPI** —— 直接由类型注解生成 OpenAPI 文档，`/docs` 开箱可用，省掉手写接口文档；依赖注入（`Depends`）天然适配"每个请求一个数据库会话"的 Web 场景；原生基于 Pydantic，让 View 层可以用声明代替序列化代码。

**SQLAlchemy 2.0** —— ORM 把表结构与 Python 类绑定，模型即文档；`Mapped` 类型注解能在 IDE 里补全字段名，配合 `select()` 新风格写出可组合的查询。会话与事务边界清晰（`sessionmaker` 交给 `get_db()` 管理），逻辑删除只需在基类查询里加一个过滤条件，而 `unique_specs` 这类跨表规则也能在 CRUD 基类里一次实现、五张表复用。

**Pydantic v2** —— 入参校验和出参契约用同一套模型语言表达，避免"校验一遍、序列化再写一遍"的重复；`response_model` 会在返回前过滤未声明字段并做类型转换，把 View 层契约真正**落到运行时**，而不是停留在注释里。`pydantic-settings` 则让 `.env` 读取带类型校验和默认值，配置项写错在启动时就会报错，而非运行到一半才失败。

**MySQL** —— 五张表之间是典型的强关系型结构（学生→班级、成绩→学生+教师、就业→学生），外键与聚合统计（`/stats/*` 的分组、连接、均值）都是关系库的强项。

**httpx** —— `/gateway` 需要异步发起 HTTP 请求，与 FastAPI 的异步模型一致，避免在协程里用同步客户端阻塞事件循环。
