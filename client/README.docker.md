# Docker 部署指南

## 快速开始

### 1. 构建镜像

```bash
cd gpu-monitor/client
docker build -t gpu-monitor-client .
```

### 2. 运行容器（无 GPU）

如果不需要监控 GPU，直接运行：

```bash
docker run -d \
  --name gpu-monitor-client \
  --network host \
  -p 9527:9527 \
  gpu-monitor-client
```

### 3. 运行容器（带 GPU 监控）

需要先在宿主机安装 **NVIDIA Container Toolkit**：

```bash
# Ubuntu/Debian 安装 NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

然后带 GPU 运行：

```bash
docker run -d \
  --name gpu-monitor-client \
  --network host \
  --gpus all \
  -p 9527:9527 \
  gpu-monitor-client
```

## 常用命令

```bash
# 查看日志
docker logs -f gpu-monitor-client

# 停止容器
docker stop gpu-monitor-client

# 删除容器
docker rm gpu-monitor-client

# 重启容器
docker restart gpu-monitor-client
```

## Docker Compose（推荐）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  gpu-monitor-client:
    build: .
    container_name: gpu-monitor-client
    network_mode: host
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
```

运行：

```bash
docker-compose up -d
```

## 注意事项

1. **网络模式**: 使用 `--network host` 可以让容器直接使用宿主机的网络，避免端口映射问题
2. **GPU 支持**: 必须安装 NVIDIA Container Toolkit 才能在容器内使用 `nvidia-smi`
3. **防火墙**: 确保宿主机的 9527 端口对外开放
4. **无 GPU 机器**: 容器会自动检测，无 GPU 时 GPU 相关指标显示为 0
