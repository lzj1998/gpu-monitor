#!/usr/bin/env python3
"""
GPU集群监控 - 客户端
后台运行，等待服务端监控指令
"""

import socket
import json
import psutil
import subprocess
import sys
import threading
import time

# 配置
DEFAULT_PORT = 9527
BUFFER_SIZE = 4096


def get_gpu_info():
    """获取NVIDIA GPU信息"""
    gpu_info = {
        'gpu_util': 0,
        'gpu_mem_util': 0,
        'gpu_temp': 0,
        'gpu_power': 0,
        'gpu_count': 0
    }
    
    try:
        # 使用nvidia-smi获取GPU信息
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,count',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines and lines[0]:
                # 取第一个GPU的数据
                parts = [p.strip() for p in lines[0].split(',')]
                if len(parts) >= 5:
                    gpu_info['gpu_util'] = float(parts[0]) if parts[0] else 0
                    mem_used = float(parts[1]) if parts[1] else 0
                    mem_total = float(parts[2]) if parts[2] else 1
                    gpu_info['gpu_mem_util'] = (mem_used / mem_total * 100) if mem_total > 0 else 0
                    gpu_info['gpu_temp'] = float(parts[3]) if parts[3] else 0
                    gpu_info['gpu_power'] = float(parts[4]) if parts[4] else 0
                    gpu_info['gpu_count'] = int(parts[5]) if len(parts) > 5 and parts[5] else len(lines)
    except Exception as e:
        pass  # GPU不可用
    
    return gpu_info


def get_system_info():
    """获取系统监控信息"""
    info = {
        'hostname': socket.gethostname(),
        'cpu_percent': psutil.cpu_percent(interval=0.5),
        'memory_percent': psutil.virtual_memory().percent,
        'load1': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
        'timestamp': time.time()
    }
    
    # 合并GPU信息
    info.update(get_gpu_info())
    
    return info


def handle_client(conn, addr):
    """处理服务端请求"""
    try:
        data = conn.recv(BUFFER_SIZE).decode('utf-8').strip()
        
        if data == 'GET_STATS':
            # 返回监控数据
            stats = get_system_info()
            response = json.dumps(stats)
            conn.sendall(response.encode('utf-8'))
        else:
            conn.sendall(b'UNKNOWN_COMMAND')
            
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 处理请求出错: {e}")
    finally:
        conn.close()


def start_client(port=DEFAULT_PORT):
    """启动客户端服务"""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(5)
        print(f"[*] GPU监控客户端已启动，监听端口 {port}")
        print(f"[*] 按 Ctrl+C 停止服务")
        
        while True:
            conn, addr = server_socket.accept()
            # 使用线程处理每个连接
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n[*] 正在关闭客户端...")
    except Exception as e:
        print(f"[!] 错误: {e}")
    finally:
        server_socket.close()


if __name__ == '__main__':
    import os
    
    # 检查后台运行参数
    if len(sys.argv) > 1 and sys.argv[1] == '-d':
        # 后台运行
        pid = os.fork()
        if pid > 0:
            print(f"[*] 客户端已在后台运行，PID: {pid}")
            sys.exit(0)
        
        # 子进程
        os.setsid()
        os.umask(0)
        
        # 第二次fork
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
        
        # 重定向标准输出/错误
        sys.stdout.flush()
        sys.stderr.flush()
        
        import logging
        logging.basicConfig(
            filename='/tmp/gpu-monitor-client.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        
        # 替换print为logging
        class LoggerWriter:
            def write(self, message):
                if message.strip():
                    logging.info(message.strip())
            def flush(self):
                pass
        
        sys.stdout = LoggerWriter()
        sys.stderr = LoggerWriter()
    
    start_client()
