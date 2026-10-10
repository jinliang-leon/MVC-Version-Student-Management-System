# 数据库设计

数据库：MySQL 8，库名默认 `student_management`。共 **5 张业务表**，均由 SQLAlchemy ORM 定义（`app/models/`），服务启动时通过 `Base.metadata.create_all()` 自动建表。

## 各表用途

| 表名 | 中文名 | 用途 |
|---|---|---|
| `class` | 班级表 | 存放班级基本信息（名称、年级、备注），是学生归属的上级单位 |
| `student` | 学生表 | 存放学生基本信息，通过 `class_id` 归属到某个班级 |
| `teacher` | 教师表 | 存放教师基本信息（职称、授课科目），被成绩表引用 |
| `score` | 成绩表 | 存放「某学生某科目由某教师评分」的成绩记录，是学生与教师的多对多载体 |
| `employment` | 就业表 | 存放学生的就业记录（单位、岗位、薪资、入职日期） |

所有表均由 `app/models/base.py` 的 `TimestampMixin` 统一注入 `created_at`、`updated_at`、`is_deleted` 三个字段，下表按此统一列出。

---

## 1. class（班级表）

| 字段名 | 数据类型 | 主键 | 允许为空 | 默认值 | 字段说明 |
|---|---|---|---|---|---|
| `class_id` | Integer | ✅ | 否 | 自增 | 班级主键ID |
| `class_name` | String(100) | — | 否 | — | 班级名称 |
| `grade` | String(50) | — | 是 | NULL | 所属年级 |
| `remark` | String(500) | — | 是 | NULL | 班级备注信息 |
| `created_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 创建时间 |
| `updated_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 更新时间（由 ORM 在 UPDATE 时写入） |
| `is_deleted` | Boolean（索引） | — | 否 | `0` | 逻辑删除标记：0-正常，1-已删除 |

**关联**：一个班级可包含多名学生（`student.class_id → class.class_id`）。

## 2. student（学生表）

| 字段名 | 数据类型 | 主键 | 允许为空 | 默认值 | 字段说明 |
|---|---|---|---|---|---|
| `student_id` | Integer | ✅ | 否 | 自增 | 学生主键ID |
| `name` | String(50)（索引） | — | 否 | — | 学生姓名 |
| `gender` | String(10) | — | 是 | NULL | 学生性别（男/女） |
| `age` | Integer | — | 是 | NULL | 学生年龄 |
| `class_id` | Integer（外键 + 索引） | — | 是 | NULL | 所属班级ID → `class.class_id` |
| `created_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 创建时间 |
| `updated_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 更新时间 |
| `is_deleted` | Boolean（索引） | — | 否 | `0` | 逻辑删除标记 |

**关联**：一名学生只属于一个班级；一名学生可有多条成绩记录、多条就业记录。

## 3. teacher（教师表）

| 字段名 | 数据类型 | 主键 | 允许为空 | 默认值 | 字段说明 |
|---|---|---|---|---|---|
| `teacher_id` | Integer | ✅ | 否 | 自增 | 教师主键ID |
| `name` | String(50)（索引） | — | 否 | — | 教师姓名 |
| `title` | String(50) | — | 是 | NULL | 教师职称 |
| `subject` | String(50) | — | 是 | NULL | 授课科目 |
| `created_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 创建时间 |
| `updated_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 更新时间 |
| `is_deleted` | Boolean（索引） | — | 否 | `0` | 逻辑删除标记 |

**关联**：一名教师可对应多条成绩记录。

## 4. score（成绩表）

| 字段名 | 数据类型 | 主键 | 允许为空 | 默认值 | 字段说明 |
|---|---|---|---|---|---|
| `score_id` | Integer | ✅ | 否 | 自增 | 成绩主键ID |
| `student_id` | Integer（外键 + 索引） | — | 否 | — | 学生ID → `student.student_id` |
| `teacher_id` | Integer（外键 + 索引） | — | 否 | — | 授课教师ID → `teacher.teacher_id` |
| `subject` | String(50)（索引） | — | 否 | — | 考试科目 |
| `score` | Float | — | 否 | — | 考试分数 |
| `created_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 创建时间 |
| `updated_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 更新时间 |
| `is_deleted` | Boolean（索引） | — | 否 | `0` | 逻辑删除标记 |

**关联**：`student_id`、`teacher_id` 均非空，即每条成绩必须同时挂在一个学生和一名教师上。

## 5. employment（就业表）

| 字段名 | 数据类型 | 主键 | 允许为空 | 默认值 | 字段说明 |
|---|---|---|---|---|---|
| `employment_id` | Integer | ✅ | 否 | 自增 | 就业记录主键ID |
| `student_id` | Integer（外键 + 索引） | — | 否 | — | 学生ID → `student.student_id` |
| `company` | String(200)（索引） | — | 否 | — | 就业单位名称 |
| `position` | String(100) | — | 是 | NULL | 就职岗位 |
| `salary` | Float | — | 是 | NULL | 薪资待遇 |
| `employ_date` | Date | — | 是 | NULL | 入职日期 |
| `created_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 创建时间 |
| `updated_at` | DateTime | — | 否 | `CURRENT_TIMESTAMP` | 更新时间 |
| `is_deleted` | Boolean（索引） | — | 否 | `0` | 逻辑删除标记 |

**关联**：一条就业记录只属于一名学生；同一名学生可有多条就业记录（对应不同单位）。

---

## ER 图（文字版）

```
                ┌──────────────────┐
                │      class       │
                │  class_id  (PK)  │
                │  class_name      │
                │  grade           │
                │  remark          │
                └────────┬─────────┘
                         │ 1
                         │        「一个班级有多名学生」
                         │ N
                ┌────────▼─────────┐
                │     student      │
                │ student_id (PK)  │
                │ name  gender  age│
                └───┬──────────┬───┘
                    │ 1        │ 1
                    │          │
        「一名学生        │          │        「一名学生
          可有多条成绩」   │ N        │ N        可有多条就业记录」
            ┌───────▼──────┐    ┌──────▼────────────┐
            │    score     │    │    employment     │
            │ score_id (PK)│    │ employment_id(PK) │
            │ student_id FK│    │ student_id    FK  │
            │ teacher_id FK│    │ company  position │
            │ subject score│    │ salary  employ_date│
            └───────┬──────┘    └───────────────────┘
                    │ N
                    │        「一名教师可对应多条成绩」
                    │ 1
            ┌───────▼──────┐
            │   teacher    │
            │ teacher_id(PK)│
            │ name  title  │
            │ subject      │
            └──────────────┘
```

### 外键关系明细

| 关系 | 从表.字段 | 引用 | 基数 | 可空 | ON DELETE | ON UPDATE |
|---|---|---|---|---|---|---|
| 班级—学生 | `student.class_id` | `class.class_id` | N : 1 | 是 | `SET NULL` | `CASCADE` |
| 学生—成绩 | `score.student_id` | `student.student_id` | N : 1 | 否 | `CASCADE` | `CASCADE` |
| 教师—成绩 | `score.teacher_id` | `teacher.teacher_id` | N : 1 | 否 | `CASCADE` | `CASCADE` |
| 学生—就业 | `employment.student_id` | `student.student_id` | N : 1 | 否 | `CASCADE` | `CASCADE` |

关系汇总：

- `class` 1 ── N `student`
- `student` 1 ── N `score`
- `teacher` 1 ── N `score`（`score` 因此是学生与教师的关联表，携带“科目 + 分数”属性）
- `student` 1 ── N `employment`

---

## 约束与设计说明

### 1. 逻辑删除，不是物理删除

所有表都有 `is_deleted`。删除接口（`DELETE`）只把该字段置 `1`，数据行保留，可通过 `restore` 接口恢复。

因此 ORM 关系上做了过滤——`Class.students`、`Student.scores`、`Student.employments`、`Teacher.scores` 的 `primaryjoin` 都带 `is_deleted == False`，即**已逻辑删除的子记录不会出现在父对象的关系列表里**。查询时默认也过滤 `is_deleted = 0`，只有显式传 `include_deleted=true` 才会带出。

### 2. 唯一性约束应用层实现，数据库未加 UNIQUE 索引

数据库层面没有建任何 UNIQUE 索引，唯一性由 `app/crud/base.py` 的 `unique_specs` 在写入前校验，命中则抛 409：

| 表 | 唯一规则 | 提示信息 |
|---|---|---|
| `class` | `class_name` | 班级名称「{class_name}」已存在，不可重复创建 |
| `student` | `name` | 学生姓名「{name}」已存在，不可重复创建 |
| `teacher` | `name` | 教师姓名「{name}」已存在，不可重复创建 |
| `score` | `student_id` + `subject` | 学生 {student_id} 在科目「{subject}」已有成绩记录，不可重复录入 |
| `employment` | `student_id` + `company` | 学生 {student_id} 已有「{company}」的就业记录，不可重复创建 |

规则只统计 `is_deleted = 0` 的记录，所以「先删掉再重建同名记录」是允许的；恢复（restore）时也会校验，若与现有未删除记录重名则拒绝。

### 3. 外键的 `ON DELETE` 行为实际很少触发

由于删除走的是逻辑删除，`ON DELETE CASCADE` / `SET NULL` 只在**物理删除**（`CRUDBase.hard_delete`，当前无接口调用）时才生效。

真实的关联保护由业务规则承担：删除班级前会先检查班内是否还有未删除的学生，有则拒绝（400）。

### 4. 数值范围校验在应用层

`age`（1~150）、`score`（0~750）、`salary`（≥0）等范围限制写在 Pydantic 校验里（`app/schemas/`），数据库列**没有** CHECK 约束。若绕过 API 直接写库，这些范围不会被拦截。

### 5. 字段长度

`String(n)` 的长度限制（如 `company` 200、`remark` 500、`name` 50）在 ORM 中已声明，`create_all()` 建表时会落成对应的 `VARCHAR(n)`。
