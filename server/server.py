#!/usr/bin/env python3
"""
GPU集群监控 - 服务端
连接多个客户端，实时显示监控信息
支持多GPU汇总/分开显示模式
"""

import socket
import json
import sys
import time
import os
from datetime import datetime
from threading import Thread, Lock
import argparse

# 配置
DEFAULT_PORT = 9527
TIMEOUT = 3  # 连接超时时间
REFRESH_INTERVAL = 1  # 刷新间隔（秒）

# 颜色代码
COLORS = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'bg_red': '\033[41m',
    'bg_green': '\033[42m',
    'bg_yellow': '\033[43m'
}


def format_bytes(mb):
    """将MB转换为易读格式"""
    if mb >= 1024:
        return f"{mb/1024:.1f}G"
    else:
        return f"{mb:.0f}M"


class ClientMonitor:
    """客户端监控类"""
    
    def __init__(self, ip, port=DEFAULT_PORT):
        self.ip = ip
        self.port = port
        self.data = {}
        self.status = 'CONNECTING'
        self.last_update = 0
        self.lock = Lock()
    
    def fetch_data(self):
        """从客户端获取数据"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((self.ip, self.port))
            sock.sendall(b'GET_STATS')
            
            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            
            sock.close()
            
            data = json.loads(response.decode('utf-8'))
            
            with self.lock:
                self.data = data
                self.status = 'ONLINE'
                self.last_update = time.time()
                
        except socket.timeout:
            with self.lock:
                self.status = 'TIMEOUT'
        except ConnectionRefusedError:
            with self.lock:
                self.status = 'REFUSED'
        except Exception as e:
            with self.lock:
                self.status = 'ERROR'
    
    def get_display_data(self, multi_gpu_mode='summary'):
        """获取用于显示的数据
        
        multi_gpu_mode: 'summary' - 汇总显示, 'detail' - 分开显示每个GPU
        """
        with self.lock:
            if self.status != 'ONLINE':
                return [{
                    'ip': self.ip,
                    'hostname': '-',
                    'cpu': '-',
                    'mem': '-',
                    'gpu': '-',
                    'gpu_mem': '-',
                    'gpu_temp': '-',
                    'gpu_power': '-',
                    'disk_read': '-',
                    'disk_write': '-',
                    'load1': '-',
                    'status': self.status,
                    'gpu_index': None
                }]
            
            base_data = {
                'ip': self.ip,
                'hostname': self.data.get('hostname', '-')[:12],
                'cpu': self.data.get('cpu_percent', 0),
                'mem': self.data.get('memory_percent', 0),
                'disk_read': self.data.get('disk_read_mbps', 0),
                'disk_write': self.data.get('disk_write_mbps', 0),
                'status': 'ONLINE'
            }
            
            gpu_count = self.data.get('gpu_count', 0)
            gpus = self.data.get('gpus', [])
            
            if multi_gpu_mode == 'detail' and gpu_count > 1:
                # 分开显示每个GPU
                result = []
                for i, gpu in enumerate(gpus):
                    row = base_data.copy()
                    row['gpu'] = gpu.get('util', 0)
                    row['gpu_mem'] = f"{format_bytes(gpu.get('mem_used', 0))}/{format_bytes(gpu.get('mem_total', 0))}"
                    row['gpu_temp'] = gpu.get('temp', 0)
                    row['gpu_power'] = gpu.get('power', 0)
                    row['gpu_index'] = gpu.get('index', i)
                    result.append(row)
                return result
            else:
                # 汇总显示
                row = base_data.copy()
                row['gpu'] = self.data.get('gpu_util', 0)
                mem_used = self.data.get('gpu_mem_used', 0)
                mem_total = self.data.get('gpu_mem_total', 0)
                row['gpu_mem'] = f"{format_bytes(mem_used)}/{format_bytes(mem_total)}"
                row['gpu_temp'] = self.data.get('gpu_temp', 0)
                row['gpu_power'] = self.data.get('gpu_power', 0)
                row['gpu_index'] = None
                return [row]


def colorize(value, warning=70, critical=85, suffix='', width=6):
    """根据数值添加颜色"""
    if isinstance(value, str):
        return f"{value:>{width}}"
    
    color = COLORS['green']
    if isinstance(value, (int, float)):
        if value >= critical:
            color = COLORS['red']
        elif value >= warning:
            color = COLORS['yellow']
    
    if suffix:
        return f"{color}{value:>{width-len(suffix)}}{suffix}{COLORS['reset']}"
    else:
        return f"{color}{value:>{width}}{COLORS['reset']}"


def color_status(status):
    """状态着色"""
    if status == 'ONLINE':
        return f"{COLORS['green']}{status:<8}{COLORS['reset']}"
    elif status in ['TIMEOUT', 'ERROR']:
        return f"{COLORS['red']}{status:<8}{COLORS['reset']}"
    else:
        return f"{COLORS['yellow']}{status:<8}{COLORS['reset']}"


def clear_screen():
    """清屏"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header(multi_gpu_mode='summary'):
    """打印表头"""
    if multi_gpu_mode == 'detail':
        # 多GPU详细模式，显示GPU序号
        header = (
            f"{COLORS['bold']}{COLORS['cyan']}"
            f"{'IP':<16} "
            f"{'Hostname':<12} "
            f"{'GPU#':>4} "
            f"{'CPU':>6} "
            f"{'MEM':>6} "
            f"{'GPU':>6} "
            f"{'GPU-Mem':>12} "
            f"{'Temp':>5} "
            f"{'Power':>7} "
            f"{'DiskR':>7} "
            f"{'DiskW':>7} "
            f"{'Status':<8}"
            f"{COLORS['reset']}"
        )
        print(header)
        print("-" * 105)
    else:
        # 汇总模式
        header = (
            f"{COLORS['bold']}{COLORS['cyan']}"
            f"{'IP':<16} "
            f"{'Hostname':<12} "
            f"{'CPU':>6} "
            f"{'MEM':>6} "
            f"{'GPU':>6} "
            f"{'GPU-Mem':>12} "
            f"{'Temp':>5} "
            f"{'Power':>7} "
            f"{'DiskR':>7} "
            f"{'DiskW':>7} "
            f"{'Status':<8}"
            f"{COLORS['reset']}"
        )
        print(header)
        print("-" * 100)


def print_client_row(data, multi_gpu_mode='summary'):
    """打印客户端数据行"""
    if data['status'] != 'ONLINE':
        if multi_gpu_mode == 'detail':
            row = (
                f"{data['ip']:<16} "
                f"{'-':<12} "
                f"{'-':>4} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'-':>12} "
                f"{'-':>5} "
                f"{'-':>7} "
                f"{'-':>7} "
                f"{'-':>7} "
                f"{color_status(data['status'])}"
            )
        else:
            row = (
                f"{data['ip']:<16} "
                f"{'-':<12} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'-':>12} "
                f"{'-':>5} "
                f"{'-':>7} "
                f"{'-':>7} "
                f"{'-':>7} "
                f"{color_status(data['status'])}"
            )
    else:
        gpu_index_str = str(data.get('gpu_index', '')) if data.get('gpu_index') is not None else '-'
        
        if multi_gpu_mode == 'detail':
            row = (
                f"{data['ip']:<16} "
                f"{data['hostname']:<12} "
                f"{gpu_index_str:>4} "
                f"{colorize(data['cpu'], 70, 85, '%', 6)} "
                f"{colorize(data['mem'], 80, 90, '%', 6)} "
                f"{colorize(data['gpu'], 80, 95, '%', 6)} "
                f"{data['gpu_mem']:>12} "
                f"{colorize(data['gpu_temp'], 70, 80, '', 5)} "
                f"{colorize(data['gpu_power'], 200, 300, 'W', 7)} "
                f"{data['disk_read']:>6.1f} "
                f"{data['disk_write']:>6.1f} "
                f"{color_status(data['status'])}"
            )
        else:
            row = (
                f"{data['ip']:<16} "
                f"{data['hostname']:<12} "
                f"{colorize(data['cpu'], 70, 85, '%', 6)} "
                f"{colorize(data['mem'], 80, 90, '%', 6)} "
                f"{colorize(data['gpu'], 80, 95, '%', 6)} "
                f"{data['gpu_mem']:>12} "
                f"{colorize(data['gpu_temp'], 70, 80, '', 5)} "
                f"{colorize(data['gpu_power'], 200, 300, 'W', 7)} "
                f"{data['disk_read']:>6.1f} "
                f"{data['disk_write']:>6.1f} "
                f"{color_status(data['status'])}"
            )
    print(row)


def load_ip_list(filepath):
    """从文件加载IP列表"""
    ips = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ips.append(line)
    except FileNotFoundError:
        print(f"[!] 错误: 找不到文件 {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"[!] 错误: 读取文件失败 - {e}")
        sys.exit(1)
    
    return ips


def monitor_loop(clients, multi_gpu_mode='summary'):
    """监控主循环"""
    try:
        while True:
            clear_screen()
            
            # 打印标题
            print(f"{COLORS['bold']}{COLORS['magenta']}")
            print("╔══════════════════════════════════════════════════════════════════════════════╗")
            mode_str = "[多GPU详细模式]" if multi_gpu_mode == 'detail' else "[汇总模式]"
            print(f"║                    GPU Cluster Monitor v1.1  {mode_str:<25}     ║")
            print(f"║                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<47}     ║")
            print("╚══════════════════════════════════════════════════════════════════════════════╝")
            print(f"{COLORS['reset']}")
            
            print_header(multi_gpu_mode)
            
            # 获取并显示每个客户端的数据
            for client in clients:
                rows = client.get_display_data(multi_gpu_mode)
                for data in rows:
                    print_client_row(data, multi_gpu_mode)
            
            if multi_gpu_mode == 'detail':
                print("-" * 105)
            else:
                print("-" * 100)
            print(f"\n按 Ctrl+C 退出 | 模式: {multi_gpu_mode} | 客户端数: {len(clients)}")
            
            # 等待刷新
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n[*] 监控已停止")


def main():
    parser = argparse.ArgumentParser(description='GPU集群监控服务端')
    parser.add_argument('ipfile', help='包含客户端IP列表的文件（每行一个IP）')
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f'客户端端口 (默认: {DEFAULT_PORT})')
    parser.add_argument('-i', '--interval', type=int, default=REFRESH_INTERVAL,
                        help=f'刷新间隔秒数 (默认: {REFRESH_INTERVAL})')
    parser.add_argument('-m', '--multi-gpu', choices=['summary', 'detail'], default='summary',
                        help='多GPU显示模式: summary=汇总, detail=分开显示 (默认: summary)')
    
    args = parser.parse_args()
    
    # 加载IP列表
    ips = load_ip_list(args.ipfile)
    if not ips:
        print("[!] 错误: IP列表为空")
        sys.exit(1)
    
    print(f"[*] 加载了 {len(ips)} 个客户端IP")
    print(f"[*] 多GPU模式: {args.multi_gpu}")
    print(f"[*] 正在初始化监控...")
    
    # 创建客户端监控对象
    clients = [ClientMonitor(ip, args.port) for ip in ips]
    
    # 启动数据获取线程
    def fetch_worker(client):
        while True:
            client.fetch_data()
            time.sleep(args.interval)
    
    for client in clients:
        thread = Thread(target=fetch_worker, args=(client,), daemon=True)
        thread.start()
    
    # 给初始连接一点时间
    time.sleep(0.5)
    
    # 进入监控循环
    monitor_loop(clients, args.multi_gpu)


if __name__ == '__main__':
    main()
