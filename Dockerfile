# V2.0 Pro: NVIDIA CUDA base for GPU acceleration
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/root/.cache/huggingface \
    TRANSFORMERS_CACHE=/root/.cache/huggingface \
    DEBIAN_FRONTEND=noninteractive

# 安装 Python 3.10 and system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libheif-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 创建 python3 -> python3.10 符号链接
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# 升级 pip
RUN python3 -m pip install --upgrade pip

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖 (这会花一些时间,因为有 PyTorch CUDA 版本)
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# 创建必要的目录
RUN mkdir -p /app/photos /app/chroma_db /root/.cache/huggingface

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
