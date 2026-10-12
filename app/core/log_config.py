"""统一日志配置

提供一套「开箱即用」的日志配置：同时输出到控制台与滚动文件，全局统一格式。

特性
----
- 控制台 + 文件 双输出
- 文件滚动：按天切分（默认，保留最近 N 天）或按大小切分，二选一
- 日志级别可配置（DEBUG / INFO / WARNING / ERROR）
- 格式清晰：时间 | 级别 | 模块名:行号 | 消息

用法
----
在应用入口 main.py 启动时调用一次即可：:

    from app.core.log_config import setup_logging
    setup_logging()               # 缺省从 settings 读取；也可临时覆盖参数

业务代码中的标准写法（services / controllers / crud 通用）::

    import logging
    logger = logging.getLogger(__name__)   # 用模块名作 logger 名，便于按模块过滤

    logger.debug("查询参数 page=%s size=%s", page, size)   # 开发排查，INFO 下不输出
    logger.info("学生创建成功 student_id=%d", sid)          # 关键业务动作
    logger.warning("班级 %s 已逻辑删除，跳过统计", name)      # 可恢复的异常情况
    logger.error("保存成绩失败: %s", exc, exc_info=True)    # 需关注的错误（带堆栈）

约定
----
- 用 %s/%d 占位符惰性拼接，不要写 "..." + str(x)：级别不匹配时省去拼接开销。
- 只有处于 except 分支才用 exc_info=True（或 logger.exception），否则会产生无意义堆栈。
- 日志级别、目录、切分策略均由 app/core/config.py 的 LOG_* 字段驱动（可在 .env 覆盖）。
"""
import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings

# 统一日志格式：时间 | 级别 | 模块名:行号 | 消息
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 压低第三方库噪音（可按需增删）：uvicorn 的逐请求访问日志较吵，只保留 WARNING 及以上
_QUIET_LOGGERS = {"uvicorn.access": logging.WARNING}


def _resolve_level(level: str | int | None) -> int:
    """把 'INFO' / logging.INFO 统一转成级别常量"""
    if level is None:
        level = settings.LOG_LEVEL
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    if not isinstance(level, int):
        raise ValueError(f"非法的日志级别: {level!r}")
    return level


def setup_logging(
    *,
    level: str | int | None = None,
    log_dir: str | None = None,
    log_file: str | None = None,
    rotation: str | None = None,      # "time"=按天切分 / "size"=按大小切分
    backup_count: int | None = None,
    max_bytes: int | None = None,
) -> None:
    """初始化全局日志（幂等，可重复调用；缺省参数从 settings 读取）"""
    level = _resolve_level(level)
    log_dir = settings.LOG_DIR if log_dir is None else log_dir
    log_file = settings.LOG_FILE if log_file is None else log_file
    rotation = settings.LOG_ROTATION if rotation is None else rotation
    backup_count = settings.LOG_BACKUP_COUNT if backup_count is None else backup_count
    max_bytes = settings.LOG_MAX_BYTES if max_bytes is None else max_bytes

    # 日志目录相对路径时锚定项目根目录，避免受启动时工作目录影响
    base = Path(log_dir)
    if not base.is_absolute():
        base = PROJECT_ROOT / base
    base.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    # 文件 handler：按大小或按天滚动（默认按天，保留最近 N 个备份）
    path = base / log_file
    if rotation == "size":
        file_handler = RotatingFileHandler(
            path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    else:  # "time"（默认）
        file_handler = TimedRotatingFileHandler(
            path,
            when="midnight",           # 每天凌晨切分
            interval=1,
            backupCount=backup_count,  # 保留最近 N 个备份（约 N 天）
            encoding="utf-8",
        )
    file_handler.setFormatter(formatter)

    # 配置根 logger；先清空已有 handler，保证重复调用 / uvicorn reload 时不叠加
    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()
    root.addHandler(console)
    root.addHandler(file_handler)

    # 压低第三方库日志噪音
    for name, lvl in _QUIET_LOGGERS.items():
        logging.getLogger(name).setLevel(lvl)

    logging.getLogger(__name__).info(
        "日志配置已加载：level=%s dir=%s file=%s rotation=%s",
        logging.getLevelName(level), base, log_file, rotation,
    )
