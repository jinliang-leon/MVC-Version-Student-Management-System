"""数据库连接与会话管理

- engine：全局数据库引擎
- SessionLocal：会话工厂
- get_db：FastAPI 依赖注入用的会话生成器（自动关闭连接）
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# ---------- 引擎 ----------
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,        # 开发模式打印 SQL，便于调试
    pool_pre_ping=True,         # 取连接前先 ping 探活，断线自动重连
    pool_recycle=3600,          # 连接 1 小时后回收，避免触发 MySQL 8 小时 wait_timeout
    pool_size=10,               # 连接池常驻连接数
    max_overflow=20,            # 超出 pool_size 后最多再临时创建 20 个连接
    future=True,                # 启用 SQLAlchemy 2.0 风格（本项目其余代码均按 2.0 书写）
)

# ---------- 会话工厂 ----------
# 三个开关的取值是刻意选择，理解后勿随意改动：
# - autocommit=False：关闭自动提交，写操作需显式 commit（本项目在 CRUD 中统一提交）；
# - autoflush=False：关闭自动 flush，避免查询前被隐式写入，行为更可预期；
# - expire_on_commit=False：commit 后不失效已加载对象的属性，便于提交后继续使用同一实例。
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类（SQLAlchemy 2.0 风格）"""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话，请求结束后自动关闭

    用法::

        @router.get("/")
        def list_all(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
