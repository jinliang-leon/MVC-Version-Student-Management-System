"""应用配置模块

使用 Pydantic Settings 从 .env 文件读取配置，支持类型校验。
"""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录 = app/ 的上一级；.env 固定放在这里，避免受启动时的工作目录影响
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- 应用信息 ----------
    APP_NAME: str = "学生管理系统"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "基于 FastAPI + SQLAlchemy + MySQL 的学生管理系统后端，"
        "提供班级、学生、教师、成绩、就业五张业务表的完整 RESTful 接口，"
        "可对接 Dify 智能对话流实现自然语言数据管理。"
    )

    # ---------- 服务 ----------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    DEBUG: bool = True

    # ---------- 数据库 ----------
    # DATABASE_URL 若提供则优先使用；否则用下面的分字段拼接（见 database_url 属性）
    DATABASE_URL: Optional[str] = None
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "student_management"

    # ---------- JWT 认证 ----------
    # 密钥务必在 .env 中配置为强随机值；生产环境务必替换默认值
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30   # access_token 有效期（分钟）

    # refresh_token 生成函数（create_refresh_token）已就绪，但登录接口当前仅签发 access_token，刷新流程待后续接入
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7   # 7 天，供 refresh_token 使用

    # ---------- 初始管理员（seed_rbac.py 使用） ----------
    # 生产环境务必修改 ADMIN_PASSWORD 为强密码
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # ---------- CORS ----------
    CORS_ORIGINS: str = "*"

    # ---------- 分页 ----------
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # ---------- 日志 ----------
    LOG_PROJECT_NAME: str = "student-management"   # 日志格式中的「项目名」
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"                           # 相对路径锚定项目根目录 -> <项目根>/logs（与 app 同级）
    LOG_FILE: str = "app.log"
    LOG_BACKUP_COUNT: int = 5                        # 滚动文件保留的备份数
    LOG_MAX_BYTES: int = 10 * 1024 * 1024            # 单个文件最大字节（10MB，RotatingFileHandler 滚动阈值）

    @property
    def database_url(self) -> str:
        """SQLAlchemy 连接串（PyMySQL 驱动）

        优先使用 DATABASE_URL；未提供时由 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME 拼接。
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        """解析 CORS 来源列表"""
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @field_validator("DB_PORT", "APP_PORT", mode="before")
    @classmethod
    def _port_must_be_valid(cls, v):
        v = int(v)
        if not (1 <= v <= 65535):
            raise ValueError("端口必须在 1~65535 之间")
        return v


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（带缓存）"""
    return Settings()


settings = get_settings()
