# GPU集群监控系统

一个简单的GPU集群监控工具，支持实时监控多台Linux服务器的CPU、内存和NVIDIA GPU状态。

## 功能特性

- **实时监控**: 1秒刷新一次，实时显示集群状态
- **彩色显示**: 根据阈值自动着色（绿色正常、黄色警告、红色危险）
- **GPU支持**: 支持NVIDIA GPU监控（利用率、显存、温度、功耗）
- **轻量级**: 纯Python实现，依赖少
- **后台运行**: 客户端可后台运行，不占用终端

## 监控指标

| 列 | 指标 | 说明 |
|---|---|---|
| IP | 客户端IP地址 | |
| Hostname | 主机名 | 截断显示前12字符 |
| CPU% | CPU使用率 | >70%黄色, >85%红色 |
| MEM% | 内存使用率 | >80%黄色, >90%红色 |
| GPU% | GPU利用率 | >80%黄色, >95%红色 |
| GPU-Mem% | GPU显存使用率 | >80%黄色, >95%红色 |
| Temp | GPU温度 | >70°C黄色, >80°C红色 |
| Power | GPU功耗 | >200W黄色, >300W红色 |
| Load1 | 1分钟负载 | |
| Status | 连接状态 | ONLINE/TIMEOUT/ERROR |

## 安装

### 1. 克隆或复制项目到所有机器

```bash
# 在服务端和所有客户端
cd gpu-monitor
pip install -r client/requirements.txt  # 客户端
pip install -r server/requirements.txt  # 服务端
```

### 2. 确保客户端有nvidia-smi

客户端机器需要安装NVIDIA驱动，确保可以运行：
```bash
nvidia-smi
```

## 使用

### 客户端（被监控机器）

```bash
# 前台运行（调试用）
python client/client.py

# 后台运行（推荐）
python client/client.py -d
```

后台运行时会将日志写入 `/tmp/gpu-monitor-client.log`

### 服务端（监控中心）

1. 创建IP列表文件：
```bash
cat > clients.txt << EOF
192.168.1.101
192.168.1.102
192.168.1.103
EOF
```

2. 启动监控：
```bash
python server/server.py clients.txt
```

可选参数：
```bash
python server/server.py clients.txt -p 9527 -i 2  # 自定义端口和刷新间隔
```

## 防火墙设置

确保客户端防火墙允许服务端连接：
```bash
# 使用iptables
iptables -A INPUT -p tcp --dport 9527 -j ACCEPT

# 或使用firewalld
firewall-cmd --add-port=9527/tcp --permanent
firewall-cmd --reload
```

## 停止客户端

```bash
# 查找进程
ps aux | grep gpu-monitor-client

# 停止进程
kill <PID>
```

## 目录结构

```
gpu-monitor/
├── client/
│   ├── client.py          # 客户端主程序
│   └── requirements.txt   # 客户端依赖
├── server/
│   ├── server.py          # 服务端主程序
│   └── requirements.txt   # 服务端依赖
└── README.md              # 说明文档
```

## 注意事项

1. 客户端和服务端默认使用 **9527** 端口通信
2. 确保服务端可以访问客户端的9527端口
3. 客户端需要安装NVIDIA驱动才能获取GPU信息
4. 无GPU的机器GPU相关指标显示为0

## License

MIT
