import sys
import os
# 把当前文件所在的上一级目录（也就是项目根目录）加入搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.response import register_exception_handlers, success

# 导入模型，确保 create_all 能识别所有表
from app.models import Class, Employment, Score, Student, Teacher  # noqa: F401

# 模块说明：端口取自 settings（.env），文档与实际端口自动同步。
# 这里用 __doc__ 赋值而非文件开头的字符串字面量：字面量在 import 之前求值，
# 那时 settings 尚未导入，无法引用 settings.APP_PORT。
__doc__ = f"""学生管理系统 - FastAPI 应用入口

启动方式：
    uvicorn app.main:app --host {settings.APP_HOST} --port {settings.APP_PORT} --reload

接口文档：
    Swagger UI : http://127.0.0.1:{settings.APP_PORT}/docs
    ReDoc      : http://127.0.0.1:{settings.APP_PORT}/redoc

管理后台：
    http://127.0.0.1:{settings.APP_PORT}/ui   （托管 frontend/index.html）
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时自动建表"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表检查/创建完成")
    except Exception as e:  # pragma: no cover
        logger.error("数据库初始化失败: %s", e)
        raise
    yield
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={"name": "学生管理系统", "url": f"http://127.0.0.1:{settings.APP_PORT}/docs"},
        lifespan=lifespan,
    )

    # ---------- CORS ----------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- 全局异常处理 ----------
    register_exception_handlers(app)

    # ---------- 路由 ----------
    app.include_router(api_router)

    # ---------- 健康检查 ----------
    @app.get("/", tags=["系统"], summary="服务信息")
    def root():
        return success(
            data={
                "app": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "docs": "/docs",
                "redoc": "/redoc",
            },
            message="学生管理系统 API 运行中",
        )

    @app.get("/health", tags=["系统"], summary="健康检查")
    def health():
        return success(data={"status": "healthy"})

    # ---------- 前端管理后台（静态托管） ----------
    # 与后端同源，省去跨域问题；访问 /ui 即可打开。
    _frontend = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    if _frontend.is_file():
        @app.get("/ui", include_in_schema=False)
        def ui_index():
            return FileResponse(_frontend, media_type="text/html")

        @app.get("/ui/", include_in_schema=False)
        def ui_index_slash():
            return RedirectResponse(url="/ui")

        logger.info("前端管理后台已挂载: /ui  ->  %s", _frontend)
    else:  # pragma: no cover
        logger.warning("未找到前端文件，跳过挂载: %s", _frontend)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
