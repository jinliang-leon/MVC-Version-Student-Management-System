# API 接口文档

Base URL：`http://127.0.0.1:8001`（端口由 `.env` 的 `APP_PORT` 决定）
在线调试：`/docs`（Swagger UI） · `/redoc` · `/openapi.json`（原始描述）

---

## 通用约定

### 统一响应格式

所有业务接口返回同一结构，HTTP 状态码与响应体 `code` 保持一致：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| 字段 | 说明 |
|---|---|
| `code` | 业务状态码，与 HTTP 状态码同值 |
| `message` | 提示信息，失败时为可读原因 |
| `data` | 业务数据，可能是对象、数组或 `null` |

**例外**：`POST /gateway` 恒返回 HTTP 200，真实状态码只体现在响应体的 `code` 中（原因见该接口说明）。

### 分页参数

列表类接口（`GET /{模块}/`）通用查询参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `page` | int | 否 | `1` | 页码，从 1 开始，最小 1 |
| `page_size` | int | 否 | `10` | 每页条数，取值 1~1000，**超过 100 会被截断为 100** |

分页返回结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 25,
    "page": 1,
    "page_size": 10,
    "total_pages": 3,
    "items": []
  }
}
```

### 逻辑删除

- 所有 `DELETE` 接口都是**逻辑删除**：仅把 `is_deleted` 置为 `1`，数据行保留。
- 列表与详情默认只返回 `is_deleted = 0` 的数据，传 `include_deleted=true` 可查到已删除数据。
- 每个模块都提供 `POST /{模块}/{id}/restore` 恢复接口（回收站）。

### 全局错误码

| code | 含义 | 触发场景 | 响应体示例 |
|---|---|---|---|
| 400 | 业务规则拒绝 | 删除还有学生的班级；恢复一条未被删除的记录 | `{"code":400,"message":"该班级下还有 3 名学生，无法删除。请先转移或删除这些学生。","data":{"class_id":1,"student_count":3}}` |
| 404 | 资源不存在 | ID 查不到（含外键指向的学生/教师/班级不存在）；或访问了不存在的路径 | `{"code":404,"message":"Student 中不存在 ID = 999 的记录","data":null}` | 
| 405 | 请求方法不允许 | 用错了 HTTP 方法 | `{"code":405,"message":"Method Not Allowed","data":null}` |
| 409 | 唯一性冲突 | 创建/更新/恢复时命中唯一规则 | `{"code":409,"message":"班级名称「Python全栈1班」已存在，不可重复创建","data":{"conflict_id":1,"class_name":"Python全栈1班"}}` |
| 422 | 参数校验失败 | 字段缺失、类型错误、超长、格式非法、范围越界 | `{"code":422,"message":"name: 姓名只能包含中文、英文字母和间隔号（·），不能是纯数字或特殊符号","data":{"errors":[{"field":"name","message":"..."}]}}` |
| 500 | 服务器内部异常 | 未捕获的异常 | `{"code":500,"message":"服务器内部异常: ...","data":null}` |
| 502 | 网关转发失败 | 仅 `/gateway`：内部转发时网络异常 | `{"code":502,"message":"网关转发失败: ...","data":null}` |

> `401` / `403` 由 RBAC 鉴权装饰器触发（见 [RBAC_USAGE.md](RBAC_USAGE.md)）：未携带 / 无效 Token 返回 `401`，Token 有效但权限不足返回 `403`，响应体同样为 `{code, message, data}` 结构。
>
> 关于 `message` 的语言：由业务代码主动抛出的异常（`UnauthorizedException` / `ForbiddenException` / `NotFoundException` / `DuplicateException` / `ConflictException` / 参数校验）都是**中文**提示；而框架层面的 `405 Method Not Allowed`、未知路径的 `404 Not Found` 会原样透出**英文**原文，例如 `{"code":405,"message":"Method Not Allowed","data":null}`。

### 请求体校验规则（写入路径）

| 字段类型 | 规则 |
|---|---|
| 姓名（学生、教师） | 非空；只允许中文、英文字母、间隔号（·）、空格及中文/全角标点；不能是纯数字（如 `13131`） |
| 通用文本（班级名、科目、公司、岗位、职称） | 非空；至少包含一个中文或英文字母；不能含 `<` `>` |
| `age` | 1~150 |
| `score` | 0~750 |
| `salary` | ≥ 0 |
| 日期字段 | `YYYY-MM-DD` |

---

## 一、系统模块

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/` | 服务信息（应用名、版本、文档地址） | 无 | — |
| GET | `/health` | 健康检查 | 无 | — |
| POST | `/gateway` | Dify 专用内部转发网关 | Body：`method`、`path`、`body`、`error` | 422、502（恒为 HTTP 200） |

### GET /

```json
{
  "code": 200,
  "message": "学生管理系统 API 运行中",
  "data": {
    "app": "学生管理系统",
    "version": "1.0.0",
    "docs": "/docs",
    "redoc": "/redoc"
  }
}
```

### GET /health

```json
{ "code": 200, "message": "success", "data": { "status": "healthy" } }
```

### POST /gateway

供 Dify 的 HTTP 请求节点调用。因为 Dify 节点的 `method` 是固定枚举、无法用变量指定，这里用单一入口按 `method` + `path` 在服务端完成转发。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `method` | string | 是 | 转发方法，枚举：`GET`/`POST`/`PUT`/`PATCH`/`DELETE` |
| `path` | string | 是 | 内部路由，可含查询串，必须以 `/` 开头；不允许 `://` 或 `//` 开头 |
| `body` | object | 否 | `POST`/`PUT`/`PATCH` 时携带的 JSON 请求体 |
| `error` | string | 否 | 非空时**不转发**，直接返回该错误信息（`code=400`） |

```json
{
  "method": "GET",
  "path": "/students/?gender=男&page=1",
  "body": null,
  "error": null
}
```

**响应（恒 HTTP 200）**：转发成功时，原样返回内部接口的响应体。

```json
{
  "code": 200,
  "message": "success",
  "data": { "total": 1, "page": 1, "page_size": 10, "total_pages": 1, "items": [] }
}
```

转发失败（内部接口返回 404）时，**HTTP 仍是 200**，看 `code`：

```json
{ "code": 404, "message": "Student 中不存在 ID = 999 的记录", "data": null }
```

`error` 短路（未发起转发）：

```json
{ "code": 400, "message": "缺少 class_id，无法确定班级", "data": null }
```

---

## 二、班级模块（/classes）

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/classes/` | 分页查询班级列表 | Query：分页参数 + `keyword`（模糊匹配 `class_name`/`grade`/`remark`）+ `include_deleted` | 422 |
| GET | `/classes/{class_id}` | 查询单个班级 | Path：`class_id`；Query：`include_deleted` | 404、422 |
| POST | `/classes/` | 新增班级 | Body：`class_name`(必填)、`grade`、`remark` | 409、422 |
| PUT | `/classes/{class_id}` | 更新班级（局部更新，只传要改的字段） | Path：`class_id`；Body：同上（全部可选） | 404、409、422 |
| DELETE | `/classes/{class_id}` | 删除班级（逻辑删除） | Path：`class_id` | **400**（班内还有学生）、404 |
| POST | `/classes/{class_id}/restore` | 恢复已删除的班级 | Path：`class_id` | 400（未被删除）、404、409（恢复后重名） |

### 数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `class_id` | int | 班级主键ID |
| `class_name` | string | 班级名称（唯一，≤100字） |
| `grade` | string\|null | 所属年级（≤50字） |
| `remark` | string\|null | 备注（≤500字） |
| `student_count` | int\|null | 班级学生人数（响应时计算，仅统计未删除学生） |
| `created_at` / `updated_at` | datetime\|null | 创建/更新时间 |
| `is_deleted` | bool\|null | 逻辑删除标记 |

### POST /classes/ — 新增

请求体：

```json
{
  "class_name": "Python全栈1班",
  "grade": "2026级",
  "remark": "主修Python后端开发方向"
}
```

响应（HTTP 201）：

```json
{
  "code": 201,
  "message": "班级创建成功",
  "data": {
    "class_name": "Python全栈1班",
    "grade": "2026级",
    "remark": "主修Python后端开发方向",
    "class_id": 1,
    "student_count": 0,
    "created_at": "2026-10-09T21:20:31",
    "updated_at": "2026-10-09T21:20:31",
    "is_deleted": false
  }
}
```

### PUT /classes/{class_id} — 更新

请求体（只传要改的字段）：

```json
{ "class_name": "Python全栈2班", "remark": "调整班级名称" }
```

响应（HTTP 200）：

```json
{
  "code": 200,
  "message": "班级更新成功",
  "data": { "class_name": "Python全栈2班", "grade": "2026级", "remark": "调整班级名称", "class_id": 1, "student_count": 0, "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:25:02", "is_deleted": false }
}
```

### GET /classes/ — 列表

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 2,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "items": [
      { "class_name": "Python全栈1班", "grade": "2026级", "remark": "主修Python后端开发方向", "class_id": 1, "student_count": 3, "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:20:31", "is_deleted": false }
    ]
  }
}
```

### DELETE /classes/{class_id} — 删除

```json
{ "code": 200, "message": "班级删除成功", "data": { "class_id": 1 } }
```

班内还有学生时拒绝（HTTP 400）：

```json
{ "code": 400, "message": "该班级下还有 3 名学生，无法删除。请先转移或删除这些学生。", "data": { "class_id": 1, "student_count": 3 } }
```

### POST /classes/{class_id}/restore — 恢复

```json
{ "code": 200, "message": "班级已恢复", "data": { "class_name": "Python全栈1班", "grade": "2026级", "remark": null, "class_id": 1, "student_count": 0, "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:30:11", "is_deleted": false } }
```

若该班级并未被删除（HTTP 400）：

```json
{ "code": 400, "message": "该班级未被删除，无需恢复", "data": null }
```

---

## 三、学生模块（/students）

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/students/` | 分页查询学生列表 | Query：分页参数 + `keyword`（模糊匹配 `name`）+ `class_id` + `gender` + `include_deleted` | 422 |
| GET | `/students/{student_id}` | 查询单个学生 | Path：`student_id`；Query：`include_deleted` | 404、422 |
| POST | `/students/` | 新增学生 | Body：`name`(必填)、`gender`、`age`、`class_id` | **404**（班级不存在）、409、422 |
| PUT | `/students/{student_id}` | 更新学生 | Path：`student_id`；Body：同上（全部可选） | 404、409、422 |
| DELETE | `/students/{student_id}` | 删除学生（逻辑删除） | Path：`student_id` | 404 |
| POST | `/students/{student_id}/restore` | 恢复已删除的学生 | Path：`student_id` | 400、404、409 |

### 数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `student_id` | int | 学生主键ID |
| `name` | string | 学生姓名（唯一，≤50字） |
| `gender` | string\|null | 性别（男/女） |
| `age` | int\|null | 年龄（1~150） |
| `class_id` | int\|null | 所属班级ID，可为 `null`（未分班） |
| `class_name` | string\|null | 所属班级名称（响应时联查得出） |
| `created_at` / `updated_at` | datetime\|null | 创建/更新时间 |
| `is_deleted` | bool\|null | 逻辑删除标记 |

### POST /students/ — 新增

请求体：

```json
{ "name": "张三", "gender": "男", "age": 18, "class_id": 1 }
```

响应（HTTP 201）：

```json
{
  "code": 201,
  "message": "学生创建成功",
  "data": {
    "name": "张三",
    "gender": "男",
    "age": 18,
    "class_id": 1,
    "student_id": 1,
    "class_name": "Python全栈1班",
    "created_at": "2026-10-09T21:20:31",
    "updated_at": "2026-10-09T21:20:31",
    "is_deleted": false
  }
}
```

`class_id` 指向不存在的班级（HTTP 404）：

```json
{ "code": 404, "message": "Class 中不存在 ID = 99 的记录", "data": null }
```

### PUT /students/{student_id} — 更新

```json
{ "age": 19, "class_id": 2 }
```

> 传 `"class_id": null` 可把学生改为「未分班」，此时不做班级存在性校验。响应结构与 POST 相同，`message` 为 `学生更新成功`。

### GET /students/ — 列表

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "items": [
      { "name": "张三", "gender": "男", "age": 18, "class_id": 1, "student_id": 1, "class_name": "Python全栈1班", "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:20:31", "is_deleted": false }
    ]
  }
}
```

### DELETE 与 restore

```json
{ "code": 200, "message": "学生删除成功", "data": { "student_id": 1 } }
```

```json
{ "code": 200, "message": "学生已恢复", "data": { "name": "张三", "gender": "男", "age": 18, "class_id": 1, "student_id": 1, "class_name": "Python全栈1班", "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:31:04", "is_deleted": false } }
```

未被删除就恢复（HTTP 400）：`{"code":400,"message":"该学生未被删除，无需恢复","data":null}`

---

## 四、教师模块（/teachers）

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/teachers/` | 分页查询教师列表 | Query：分页参数 + `keyword`（模糊匹配 `name`/`title`/`subject`）+ `subject` + `include_deleted` | 422 |
| GET | `/teachers/{teacher_id}` | 查询单个教师 | Path：`teacher_id`；Query：`include_deleted` | 404、422 |
| POST | `/teachers/` | 新增教师 | Body：`name`(必填)、`title`、`subject` | 409、422 |
| PUT | `/teachers/{teacher_id}` | 更新教师 | Path：`teacher_id`；Body：同上（全部可选） | 404、409、422 |
| DELETE | `/teachers/{teacher_id}` | 删除教师（逻辑删除） | Path：`teacher_id` | 404 |
| POST | `/teachers/{teacher_id}/restore` | 恢复已删除的教师 | Path：`teacher_id` | 400、404、409 |

### 数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `teacher_id` | int | 教师主键ID |
| `name` | string | 教师姓名（唯一，≤50字） |
| `title` | string\|null | 职称（≤50字） |
| `subject` | string\|null | 授课科目（≤50字） |
| `created_at` / `updated_at` | datetime\|null | 创建/更新时间 |
| `is_deleted` | bool\|null | 逻辑删除标记 |

### POST /teachers/ — 新增

```json
{ "name": "李老师", "title": "高级讲师", "subject": "Python" }
```

响应（HTTP 201）：

```json
{
  "code": 201,
  "message": "教师创建成功",
  "data": { "name": "李老师", "title": "高级讲师", "subject": "Python", "teacher_id": 1, "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:20:31", "is_deleted": false }
}
```

### PUT /teachers/{teacher_id} — 更新

```json
{ "title": "特级讲师" }
```

### DELETE 与 restore

```json
{ "code": 200, "message": "教师删除成功", "data": { "teacher_id": 1 } }
```

```json
{ "code": 400, "message": "该教师未被删除，无需恢复", "data": null }
```

> 列表接口的 `items` 元素结构与该模块的响应对象一致（同上 `data` 内容）。

---

## 五、成绩模块（/scores）

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/scores/` | 分页查询成绩列表 | Query：分页参数 + `keyword`（模糊匹配 `subject`）+ `student_id` + `teacher_id` + `subject` + `include_deleted` | 422 |
| GET | `/scores/{score_id}` | 查询单条成绩 | Path：`score_id`；Query：`include_deleted` | 404、422 |
| POST | `/scores/` | 新增成绩 | Body：`student_id`、`teacher_id`、`subject`、`score`（均必填） | **404**（学生/教师不存在）、409、422 |
| PUT | `/scores/{score_id}` | 更新成绩 | Path：`score_id`；Body：同上（全部可选） | 404、409、422 |
| DELETE | `/scores/{score_id}` | 删除成绩（逻辑删除） | Path：`score_id` | 404 |
| POST | `/scores/{score_id}/restore` | 恢复已删除的成绩 | Path：`score_id` | 400、404、409 |

### 数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `score_id` | int | 成绩主键ID |
| `student_id` | int | 学生ID（必须存在） |
| `teacher_id` | int | 授课教师ID（必须存在） |
| `subject` | string | 考试科目（≤50字） |
| `score` | float | 考试分数（0~750） |
| `student_name` | string\|null | 学生姓名（响应时联查得出） |
| `teacher_name` | string\|null | 教师姓名（响应时联查得出） |
| `created_at` / `updated_at` | datetime\|null | 创建/更新时间 |
| `is_deleted` | bool\|null | 逻辑删除标记 |

**唯一规则**：同一学生的同一科目只能有一条成绩（`student_id` + `subject`），重复录入返回 409。

### POST /scores/ — 新增

```json
{ "student_id": 1, "teacher_id": 1, "subject": "Python程序设计", "score": 95.5 }
```

响应（HTTP 201）：

```json
{
  "code": 201,
  "message": "成绩创建成功",
  "data": {
    "student_id": 1,
    "teacher_id": 1,
    "subject": "Python程序设计",
    "score": 95.5,
    "score_id": 1,
    "student_name": "张三",
    "teacher_name": "李老师",
    "created_at": "2026-10-09T21:20:31",
    "updated_at": "2026-10-09T21:20:31",
    "is_deleted": false
  }
}
```

外键校验失败（HTTP 404）：

```json
{ "code": 404, "message": "Student 中不存在 ID = 999 的记录", "data": null }
{ "code": 404, "message": "Teacher 中不存在 ID = 999 的记录", "data": null }
```

重复录入（HTTP 409）：

```json
{ "code": 409, "message": "学生 1 在科目「Python程序设计」已有成绩记录，不可重复录入", "data": { "conflict_id": 1, "student_id": 1, "subject": "Python程序设计" } }
```

### PUT /scores/{score_id} — 更新

```json
{ "score": 98.0 }
```

> 若改动 `student_id` 或 `teacher_id`，会重新校验对应记录是否存在。

### GET /scores/ — 列表

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "items": [
      { "student_id": 1, "teacher_id": 1, "subject": "Python程序设计", "score": 95.5, "score_id": 1, "student_name": "张三", "teacher_name": "李老师", "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:20:31", "is_deleted": false }
    ]
  }
}
```

### DELETE 与 restore

```json
{ "code": 200, "message": "成绩删除成功", "data": { "score_id": 1 } }
```

```json
{ "code": 400, "message": "该成绩未被删除，无需恢复", "data": null }
```

---

## 六、就业模块（/employments）

### 接口列表

| 方法 | 路径 | 功能说明 | 请求参数 | 错误码 |
|---|---|---|---|---|
| GET | `/employments/` | 分页查询就业记录列表 | Query：分页参数 + `keyword`（模糊匹配 `company`/`position`）+ `student_id` + `company` + `include_deleted` | 422 |
| GET | `/employments/{employment_id}` | 查询单条就业记录 | Path：`employment_id`；Query：`include_deleted` | 404、422 |
| POST | `/employments/` | 新增就业记录 | Body：`student_id`、`company`（必填）、`position`、`salary`、`employ_date` | **404**（学生不存在）、409、422 |
| PUT | `/employments/{employment_id}` | 更新就业记录 | Path：`employment_id`；Body：同上（全部可选） | 404、409、422 |
| DELETE | `/employments/{employment_id}` | 删除就业记录（逻辑删除） | Path：`employment_id` | 404 |
| POST | `/employments/{employment_id}/restore` | 恢复已删除的就业记录 | Path：`employment_id` | 400、404、409 |

### 数据字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `employment_id` | int | 就业记录主键ID |
| `student_id` | int | 学生ID（必须存在） |
| `company` | string | 就业单位名称（≤200字） |
| `position` | string\|null | 就职岗位（≤100字） |
| `salary` | float\|null | 薪资待遇（≥0，单位：元/月） |
| `employ_date` | date\|null | 入职日期，格式 `YYYY-MM-DD` |
| `student_name` | string\|null | 学生姓名（响应时联查得出） |
| `created_at` / `updated_at` | datetime\|null | 创建/更新时间 |
| `is_deleted` | bool\|null | 逻辑删除标记 |

**唯一规则**：同一学生在同一家公司的就业记录只能有一条（`student_id` + `company`），重复创建返回 409。

### POST /employments/ — 新增

```json
{
  "student_id": 1,
  "company": "深圳沃林数字科技有限公司",
  "position": "Python后端开发工程师",
  "salary": 12000.0,
  "employ_date": "2026-07-01"
}
```

响应（HTTP 201）：

```json
{
  "code": 201,
  "message": "就业记录创建成功",
  "data": {
    "student_id": 1,
    "company": "深圳沃林数字科技有限公司",
    "position": "Python后端开发工程师",
    "salary": 12000.0,
    "employ_date": "2026-07-01",
    "employment_id": 1,
    "student_name": "张三",
    "created_at": "2026-10-09T21:20:31",
    "updated_at": "2026-10-09T21:20:31",
    "is_deleted": false
  }
}
```

重复创建（HTTP 409）：

```json
{ "code": 409, "message": "学生 1 已有「深圳沃林数字科技有限公司」的就业记录，不可重复创建", "data": { "conflict_id": 1, "student_id": 1, "company": "深圳沃林数字科技有限公司" } }
```

### PUT /employments/{employment_id} — 更新

```json
{ "salary": 15000.0 }
```

### GET /employments/ — 列表

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 1,
    "page": 1,
    "page_size": 10,
    "total_pages": 1,
    "items": [
      { "student_id": 1, "company": "深圳沃林数字科技有限公司", "position": "Python后端开发工程师", "salary": 12000.0, "employ_date": "2026-07-01", "employment_id": 1, "student_name": "张三", "created_at": "2026-10-09T21:20:31", "updated_at": "2026-10-09T21:20:31", "is_deleted": false }
    ]
  }
}
```

### DELETE 与 restore

```json
{ "code": 200, "message": "就业记录删除成功", "data": { "employment_id": 1 } }
```

```json
{ "code": 400, "message": "该就业记录未被删除，无需恢复", "data": null }
```

---

## 七、统计模块（/stats）

统计接口均为 `GET`，只读、无副作用，返回 `data` 为对象或数组（不分页）。参数非法时返回 422，其余情况恒为 200。

| 方法 | 路径 | 功能说明 | 请求参数 |
|---|---|---|---|
| GET | `/stats/overview` | 总体数据概览 | 无 |
| GET | `/stats/class-count` | 各班级学生人数（按人数降序） | 无 |
| GET | `/stats/avg-score` | 按科目统计平均分 | `student_id`、`class_id`、`subject`（均可选） |
| GET | `/stats/employment-rate` | 就业率统计 | `class_id`（可选） |
| GET | `/stats/score-ranking` | 成绩排行榜（按分数降序） | `subject`（可选）、`limit`（默认 10，1~100） |
| GET | `/stats/top-salary` | 高薪就业榜（按薪资降序） | `limit`（默认 10，1~100） |

> 所有统计均只统计未逻辑删除的数据。

### GET /stats/overview

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "class_count": 3,
    "student_count": 30,
    "teacher_count": 5,
    "score_count": 60,
    "employment_count": 24,
    "avg_score": 85.32,
    "employed_student_count": 22,
    "employment_rate": 73.33
  }
}
```

| 字段 | 说明 |
|---|---|
| `class_count` / `student_count` / `teacher_count` / `score_count` / `employment_count` | 各表未删除记录数 |
| `avg_score` | 全部成绩的平均分（保留两位）；**无成绩记录时为 `null`**（不是 0） |
| `employed_student_count` | 已就业学生数（按 `student_id` 去重） |
| `employment_rate` | 就业率百分比（保留两位），学生数为 0 时为 `0.0` |

### GET /stats/class-count

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "class_id": 1, "class_name": "Python全栈1班", "grade": "2026级", "student_count": 12 },
    { "class_id": 2, "class_name": "Java开发1班", "grade": "2026级", "student_count": 9 }
  ]
}
```

### GET /stats/avg-score

`GET /stats/avg-score?subject=Python程序设计`

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "subject": "Python程序设计", "avg_score": 87.5, "max_score": 98.0, "min_score": 65.0, "record_count": 30 }
  ]
}
```

### GET /stats/employment-rate

`GET /stats/employment-rate?class_id=1`

**注意：学生数不为 0 时返回 4 个键**：

```json
{
  "code": 200,
  "message": "success",
  "data": { "student_count": 30, "employed_count": 22, "unemployed_count": 8, "employment_rate": 73.33 }
}
```

**学生数为 0 时只返回 3 个键**（历史实现如此，未作改动）：

```json
{
  "code": 200,
  "message": "success",
  "data": { "student_count": 0, "employed_count": 0, "employment_rate": 0.0 }
}
```

> 对接时请把 `unemployed_count` 视为可选字段。

### GET /stats/score-ranking

`GET /stats/score-ranking?subject=Python程序设计&limit=1`

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "rank": 1, "student_id": 3, "student_name": "李四", "class_name": "Python全栈1班", "subject": "Python程序设计", "score": 98.0 }
  ]
}
```

`rank` 从 1 开始，按 `score` 降序；`class_name` 在学生未分班时为 `null`。

### GET /stats/top-salary

`GET /stats/top-salary?limit=1`

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "rank": 1, "student_id": 3, "student_name": "李四", "company": "腾讯科技", "position": "后端开发", "salary": 25000.0, "employ_date": "2026-07-01" }
  ]
}
```

> 仅统计 `salary` 非空的记录；`employ_date` 以字符串 `YYYY-MM-DD` 返回，无值时是 `null`。

---

## 附：接口总览

| 模块 | 路径前缀 | 接口数 | 说明 |
|---|---|---|---|
| 系统 | `/`、`/health`、`/gateway` | 3 | 服务信息、健康检查、Dify 转发网关 |
| 班级 | `/classes` | 6 | 标准 CRUD + 逻辑删除 + 恢复 |
| 学生 | `/students` | 6 | 同上，另含班级外键校验 |
| 教师 | `/teachers` | 6 | 同上 |
| 成绩 | `/scores` | 6 | 同上，另含学生/教师外键校验 |
| 就业 | `/employments` | 6 | 同上，另含学生外键校验 |
| 统计 | `/stats` | 6 | 聚合查询，只读 |
| **合计** | | **39** | |

五个业务模块的接口形态完全一致：`GET 列表`、`GET 详情`、`POST 新增`（201）、`PUT 更新`、`DELETE 删除`、`POST 恢复`。
