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
import os

# 配置
DEFAULT_PORT = 9527
BUFFER_SIZE = 4096


def get_gpu_info():
    """获取NVIDIA GPU信息 - 支持多GPU"""
    gpu_info = {
        'gpu_count': 0,
        'gpus': []  # 每个GPU的详细信息
    }
    
    try:
        # 使用nvidia-smi获取所有GPU信息
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpus = []
            total_util = 0
            total_mem_used = 0
            total_mem_total = 0
            total_temp = 0
            total_power = 0
            
            for line in lines:
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 6:
                    gpu_data = {
                        'index': int(parts[0]) if parts[0] else 0,
                        'util': float(parts[1]) if parts[1] else 0,
                        'mem_used': float(parts[2]) if parts[2] else 0,
                        'mem_total': float(parts[3]) if parts[3] else 0,
                        'temp': float(parts[4]) if parts[4] else 0,
                        'power': float(parts[5]) if parts[5] else 0
                    }
                    gpus.append(gpu_data)
                    
                    # 计算汇总值
                    total_util += gpu_data['util']
                    total_mem_used += gpu_data['mem_used']
                    total_mem_total += gpu_data['mem_total']
                    total_temp += gpu_data['temp']
                    total_power += gpu_data['power']
            
            gpu_count = len(gpus)
            gpu_info['gpu_count'] = gpu_count
            gpu_info['gpus'] = gpus
            
            # 汇总数据（用于单GPU模式显示）
            if gpu_count > 0:
                gpu_info['gpu_util'] = total_util / gpu_count
                gpu_info['gpu_mem_used'] = total_mem_used  # MB
                gpu_info['gpu_mem_total'] = total_mem_total  # MB
                gpu_info['gpu_temp'] = total_temp / gpu_count
                gpu_info['gpu_power'] = total_power
            else:
                gpu_info['gpu_util'] = 0
                gpu_info['gpu_mem_used'] = 0
                gpu_info['gpu_mem_total'] = 0
                gpu_info['gpu_temp'] = 0
                gpu_info['gpu_power'] = 0
                
    except Exception as e:
        # GPU不可用，使用默认值
        gpu_info['gpu_util'] = 0
        gpu_info['gpu_mem_used'] = 0
        gpu_info['gpu_mem_total'] = 0
        gpu_info['gpu_temp'] = 0
        gpu_info['gpu_power'] = 0
    
    return gpu_info


def get_disk_io():
    """获取磁盘IO速度"""
    try:
        # 获取磁盘IO计数器
        disk_before = psutil.disk_io_counters()
        time.sleep(0.5)  # 采样间隔
        disk_after = psutil.disk_io_counters()
        
        # 计算速度 (MB/s)
        read_speed = (disk_after.read_bytes - disk_before.read_bytes) / 0.5 / 1024 / 1024
        write_speed = (disk_after.write_bytes - disk_before.write_bytes) / 0.5 / 1024 / 1024
        
        return {
            'disk_read_mbps': round(read_speed, 2),
            'disk_write_mbps': round(write_speed, 2)
        }
    except Exception as e:
        return {
            'disk_read_mbps': 0,
            'disk_write_mbps': 0
        }


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
    
    # 合并磁盘IO信息
    info.update(get_disk_io())
    
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
