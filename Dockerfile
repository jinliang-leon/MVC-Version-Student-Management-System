# ============================================================
# 学生管理系统 —— FastAPI 后端镜像
#
# 构建上下文：项目根目录（与 app/ 同级）
# 构建：docker build -t student-mgmt-app .
# ============================================================

# ---- 基础镜像：Python 3.12（Debian slim，体积较小）----
FROM python:3.12-slim

# ---- 环境变量 ----
# PYTHONDONTWRITEBYTECODE=1：不生成 .pyc，减小镜像体积
# PYTHONUNBUFFERED=1：关闭 stdout 缓冲，日志即时输出（否则 docker logs 看不到实时日志）
# PYTHONPATH=/app：让 uvicorn 能 import app.main
# TZ：与 MySQL 容器时区保持一致
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Shanghai

# ---- 安装系统依赖：tzdata 用于让 TZ 时区生效（python slim 镜像默认不含）----
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- 先复制依赖清单并安装，充分利用 Docker 层缓存 ----
# 注意：本项目的 requirements.txt 位于 app/ 目录下（而非项目根目录）
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---- 复制应用代码 ----
COPY app /app/app

# ---- 创建非 root 用户并预建日志目录，避免以 root 运行 ----
# （config.py 的日志目录默认是 <项目根>/logs，这里即 /app/logs）
RUN useradd --create-home appuser \
    && mkdir -p /app/logs \
    && chown -R appuser:appuser /app
USER appuser

# ---- 暴露端口（与默认 APP_PORT=8001 一致；如需改端口请同步改下方 CMD 与 compose 映射）----
EXPOSE 8001

# ---- 启动命令（生产不启用 --reload；多副本请用 compose scale / replicas）----
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
