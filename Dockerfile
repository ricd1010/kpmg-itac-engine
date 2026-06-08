# --- KPMG ITAC Audit Workpaper Engine Dockerfile ---
# 使用轻量级 Python 3.10 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装必要的系统级库（用于 OpenCV 和 EasyOCR）
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 拷贝依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝项目源代码
COPY src/ ./src/
COPY data/ ./data/

# 暴露 Streamlit 默认端口 8501
EXPOSE 8501

# 健康检查
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 启动 Web 服务器
# --server.address=0.0.0.0 确保容器外可以访问
ENTRYPOINT ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
