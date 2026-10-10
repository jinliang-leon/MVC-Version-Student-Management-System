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
    echo=settings.DEBUG,        # 开发模式打印 SQL
    pool_pre_ping=True,         # 断线自动重连
    pool_recycle=3600,          # 1 小时回收连接，避免 MySQL 8h 超时
    pool_size=10,
    max_overflow=20,
    future=True,
)

# ---------- 会话工厂 ----------
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
