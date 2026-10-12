"""统一日志模块

位置：app/core/logger.py
日志目录：<项目根>/logs（与 app 同级，模块导入时自动创建）
输出目标：控制台 + 滚动文件（双输出）
滚动策略：RotatingFileHandler，单文件最大 10MB，保留 5 个备份，utf-8
日志格式：时间 | 项目名 | 级别 | 文件名:行号 | 消息

本模块「导入即初始化」全局 root logger；在 main.py 也可显式调用 init_logger()。
业务代码通过 get_logger(__name__) 获取 logger 即可，无需关心 handler 配置细节。

业务代码标准写法::

    from app.core.logger import get_logger
    logger = get_logger(__name__)

    logger.debug("查询参数 page=%s size=%s", page, size)   # 开发排查，INFO 下不输出
    logger.info("学生创建成功 student_id=%s", sid)          # 关键业务动作
    logger.warning("班级 %s 已逻辑删除，跳过统计", name)      # 可恢复的异常
    logger.error("保存成绩失败: %s", exc, exc_info=True)    # 需关注的错误（带堆栈）
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings

# ----------------------------- 配置（来自 settings，可在 .env 覆盖） -----------------------------
PROJECT_NAME = getattr(settings, "LOG_PROJECT_NAME", "student-management")
LOG_LEVEL = getattr(settings, "LOG_LEVEL", "INFO")
LOG_FILE_NAME = getattr(settings, "LOG_FILE", "app.log")
LOG_MAX_BYTES = getattr(settings, "LOG_MAX_BYTES", 10 * 1024 * 1024)  # 10MB
LOG_BACKUP_COUNT = getattr(settings, "LOG_BACKUP_COUNT", 5)            # 保留 5 个备份

# 日志目录：相对路径锚定项目根目录（<根>/logs，与 app 同级）；绝对路径则直接使用
_log_dir = Path(getattr(settings, "LOG_DIR", "logs"))
LOG_DIR: Path = _log_dir if _log_dir.is_absolute() else (PROJECT_ROOT / _log_dir)
# -------------------------------------------------------------------------------------------------

# 统一格式：时间 | 项目名 | 级别 | 文件名:行号 | 消息
_LOG_FORMAT = "%(asctime)s | %(project)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class _ProjectFilter(logging.Filter):
    """将「项目名」注入每条日志记录，供格式串中的 %(project)s 使用。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.project = PROJECT_NAME
        return True


def _build_handlers() -> list[logging.Handler]:
    """构造控制台 + 滚动文件两个 handler（幂等，调用前会确保 logs 目录存在）。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)  # 自动创建 logs 目录（需求 2）
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    project_filter = _ProjectFilter()

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(project_filter)

    # 滚动文件：RotatingFileHandler，10MB / 5 备份 / utf-8（需求 3）
    file_handler = RotatingFileHandler(
        LOG_DIR / LOG_FILE_NAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(project_filter)

    return [console, file_handler]


def init_logger() -> logging.Logger:
    """初始化全局 root logger。

    幂等，可重复调用（uvicorn --reload 重新加载模块时不会叠加重复 handler）。
    """
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)
    # 先清空已有 handler，避免 reload / 重复调用时叠加
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    for h in _build_handlers():
        root.addHandler(h)
    # 压低第三方库噪音：uvicorn 的逐请求访问日志较吵，只保留 WARNING 及以上
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return root


def get_logger(name: str | None = None) -> logging.Logger:
    """获取 logger。

    传入 __name__ 得到带模块层级的 logger（便于按模块过滤）；不传则返回根项目 logger。
    所有通过本函数获取的 logger 都复用全局 handler，无需单独配置。
    """
    return logging.getLogger(name or PROJECT_NAME)


# 导入即初始化：只要 import 本模块，全局日志即就绪
init_logger()
