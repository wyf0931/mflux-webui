# 使用 Python 3.11 slim 镜像以减小体积
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Ollama API 地址（默认 host.docker.internal 以便容器访问宿主机）
    OLLAMA_HOST=http://host.docker.internal:11434 \
    # 应用端口（默认 8090）
    PORT=8090 \
    # Flask 环境
    FLASK_ENV=production

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖（使用 pip 以避免在容器中安装 uv）
RUN pip install --no-cache-dir -e .

# 复制应用代码
COPY app.py ./
COPY templates/ ./templates/
COPY static/ ./static/

# 创建 data 目录并设置权限
RUN mkdir -p /app/data/images && \
    chmod 777 /app/data /app/data/images

# 暴露端口
EXPOSE 8090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# 启动命令
CMD ["python", "app.py"]
