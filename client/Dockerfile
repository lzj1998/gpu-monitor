# GPU监控客户端 Docker 镜像
# 使用方法见 README.docker.md

FROM python:3.11-slim

# 安装基础工具（nvidia-smi 通过 NVIDIA Container Toolkit 从宿主机挂载）
RUN apt-get update && apt-get install -y \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制客户端代码
COPY client.py .

# 暴露端口
EXPOSE 9527

# 启动客户端（前台运行，Docker 自己管理后台）
CMD ["python", "client.py"]
