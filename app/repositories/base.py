"""泛型仓储基类（Repository Base）

封装通用数据访问逻辑（与具体业务无关的纯 CRUD）：
    - get        按主键查询单条（自动过滤逻辑删除）
    - get_multi  分页 + 关键词查询
    - get_all    查询全部（不分页）
    - create     新增（命中 unique_specs 规则抛 409）
    - update     局部更新（命中唯一规则抛 409）
    - soft_delete 逻辑删除
    - restore    恢复（回收站）
    - hard_delete 物理删除

所有查询默认过滤 is_deleted == False。本层不做任何业务校验、密码哈希或序列化。
"""
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.exceptions import DuplicateException, NotFoundException

ModelType = TypeVar("ModelType", bound=Base)


class RepositoryBase(Generic[ModelType]):
    """通用仓储基类

    unique_specs：唯一性规则声明，防止重复创建。示例：
        unique_specs=[
            {"fields": ("class_name",),
             "message": "班级名称「{class_name}」已存在，不可重复创建"},
        ]
    - create：命中规则 → 409
    - update：改动的字段命中规则（排除自身）→ 409
    - restore：恢复后将与现有未删除记录重名 → 409
    规则只统计 is_deleted = False 的记录；已删除的允许重建。
    """

    def __init__(
        self,
        model: Type[ModelType],
        pk_field: str = "id",
        unique_specs: Optional[List[Dict[str, Any]]] = None,
    ):
        self.model = model
        self.pk_field = pk_field
        self.unique_specs: List[Dict[str, Any]] = unique_specs or []

    # ----------------------------------------------------------
    # 查询
    # ----------------------------------------------------------
    def _pk_column(self):
        """返回模型的主键列对象（如 Student.student_id），供排序/过滤复用"""
        return getattr(self.model, self.pk_field)

    def get(self, db: Session, obj_id: int, include_deleted: bool = False) -> Optional[ModelType]:
        """按主键查询单条记录"""
        stmt = select(self.model).where(self._pk_column() == obj_id)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712
        return db.execute(stmt).scalars().first()

    def get_or_404(self, db: Session, obj_id: int, include_deleted: bool = False) -> ModelType:
        """按主键查询，不存在则抛 404"""
        obj = self.get(db, obj_id, include_deleted=include_deleted)
        if obj is None:
            raise NotFoundException(
                f"{self.model.__name__} 中不存在 ID = {obj_id} 的记录"
            )
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None,
        keyword_fields: Optional[Sequence[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False,
        order_by: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """分页查询

        :param keyword: 模糊搜索关键词
        :param keyword_fields: 参与模糊搜索的字段名列表
        :param filters: 精确过滤条件 {"class_id": 1}
        :param order_by: 排序字段（默认按主键倒序）
        :return: {total, page, page_size, total_pages, items}
        """
        conditions = []

        if not include_deleted:
            conditions.append(self.model.is_deleted == False)  # noqa: E712

        if keyword and keyword_fields:
            like = f"%{keyword}%"
            from sqlalchemy import or_

            or_conds = []
            for f in keyword_fields:
                col = getattr(self.model, f, None)
                if col is not None:
                    or_conds.append(col.like(like))
            if or_conds:
                conditions.append(or_(*or_conds))

        if filters:
            for k, v in filters.items():
                if v is None:
                    continue
                col = getattr(self.model, k, None)
                if col is not None:
                    conditions.append(col == v)

        count_stmt = select(func.count()).select_from(self.model)
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total = db.execute(count_stmt).scalar_one()

        stmt = select(self.model)
        if conditions:
            stmt = stmt.where(*conditions)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self._pk_column().desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        items: List[ModelType] = list(db.execute(stmt).scalars().all())

        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": items,
        }

    def get_all(
        self,
        db: Session,
        *,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """查询全部（不分页）"""
        stmt = select(self.model)
        conds = []
        if not include_deleted:
            conds.append(self.model.is_deleted == False)  # noqa: E712
        if filters:
            for k, v in filters.items():
                if v is None:
                    continue
                col = getattr(self.model, k, None)
                if col is not None:
                    conds.append(col == v)
        if conds:
            stmt = stmt.where(*conds)
        stmt = stmt.order_by(self._pk_column().desc())
        return list(db.execute(stmt).scalars().all())

    # ----------------------------------------------------------
    # 唯一性校验（防重复创建）
    # ----------------------------------------------------------
    def _assert_unique(
        self,
        db: Session,
        spec: Dict[str, Any],
        values: Dict[str, Any],
        exclude_id: Optional[int] = None,
    ) -> None:
        """检查唯一规则：未删除记录中若已存在同值记录则抛 409"""
        stmt = select(self.model).where(
            self.model.is_deleted == False,  # noqa: E712
            *[getattr(self.model, f) == v for f, v in values.items()],
        )
        if exclude_id is not None:
            stmt = stmt.where(self._pk_column() != exclude_id)
        existing = db.execute(stmt).scalars().first()
        if existing is not None:
            raise DuplicateException(
                message=spec["message"].format(**values),
                data={"conflict_id": getattr(existing, self.pk_field), **values},
            )

    def _check_unique_on_create(self, db: Session, data: Dict[str, Any]) -> None:
        """新增前校验全部唯一规则"""
        for spec in self.unique_specs:
            values = {f: data.get(f) for f in spec["fields"]}
            if all(v is not None for v in values.values()):
                self._assert_unique(db, spec, values)

    def _check_unique_on_update(
        self, db: Session, data: Dict[str, Any], db_obj: ModelType
    ) -> None:
        """更新前校验：仅当规则涉及的字段出现在改动中；组合字段缺省部分取当前值"""
        exclude_id = getattr(db_obj, self.pk_field)
        for spec in self.unique_specs:
            if not any(f in data for f in spec["fields"]):
                continue
            values = {f: data.get(f, getattr(db_obj, f, None)) for f in spec["fields"]}
            if all(v is not None for v in values.values()):
                self._assert_unique(db, spec, values, exclude_id=exclude_id)

    def _check_unique_on_restore(self, db: Session, db_obj: ModelType) -> None:
        """恢复前校验：恢复后不能与现有未删除记录重复"""
        exclude_id = getattr(db_obj, self.pk_field)
        for spec in self.unique_specs:
            values = {f: getattr(db_obj, f, None) for f in spec["fields"]}
            if all(v is not None for v in values.values()):
                self._assert_unique(db, spec, values, exclude_id=exclude_id)

    # ----------------------------------------------------------
    # 写入
    # ----------------------------------------------------------
    def create(self, db: Session, obj_in: Any) -> ModelType:
        """新增记录（命中唯一规则抛 409）

        obj_in 可为 Pydantic 模型或普通 dict；若为 dict，按原样展开构造 ORM 实体。
        """
        data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)
        self._check_unique_on_create(db, data)
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: ModelType, obj_in: Any) -> ModelType:
        """局部更新（只更新传入的字段；命中唯一规则抛 409）"""
        data = (
            obj_in.model_dump(exclude_unset=True)
            if hasattr(obj_in, "model_dump")
            else dict(obj_in)
        )
        self._check_unique_on_update(db, data, db_obj)
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def soft_delete(self, db: Session, db_obj: ModelType) -> ModelType:
        """逻辑删除：仅打标记，数据保留"""
        db_obj.is_deleted = True
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def restore(self, db: Session, db_obj: ModelType) -> ModelType:
        """恢复被逻辑删除的记录（若与现有未删除记录重复则抛 409）"""
        self._check_unique_on_restore(db, db_obj)
        db_obj.is_deleted = False
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def hard_delete(self, db: Session, db_obj: ModelType) -> None:
        """物理删除（慎用）"""
        db.delete(db_obj)
        db.commit()
