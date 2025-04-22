#!/usr/bin/env python3
import subprocess
import os
import signal
import sys
import threading
import time
from datetime import datetime

# 全局控制标志
should_exit = False

def get_pid(package_name):
    """通过adb获取应用的进程ID"""
    try:
        result = subprocess.run(
            f"adb shell ps -A | grep {package_name}",  # 使用-A参数查看所有进程
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split('\n')
        for line in lines:
            if package_name in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]  # 第二列是PID
        return None

    except Exception as e:
        print(f"[ERROR] 获取进程ID时出错: {e}")
        return None

def is_pid_alive(pid):
    """检查PID是否仍在运行"""
    try:
        result = subprocess.run(
            f"adb shell ps -p {pid}",
            shell=True,
            capture_output=True,
            text=True
        )
        return str(pid) in result.stdout
    except Exception:
        return False

def monitor_process(initial_pid, package_name):
    """监控进程并自动重连"""
    global should_exit
    current_pid = initial_pid
    desktop = os.path.expanduser("~/Desktop")
    output_file = os.path.join(desktop, f"{package_name}-top-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt")
    process = None

    def cleanup():
        """清理进程资源"""
        if process and process.poll() is None:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass

    def input_listener():
        """监听用户输入"""
        global should_exit
        while not should_exit:
            user_input = input().lower()
            if user_input in ('q', 'quit', 'exit'):
                should_exit = True
                cleanup()
                break

    # 创建输出目录
    os.makedirs(desktop, exist_ok=True)

    # 启动输入监听线程
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()

    print(f"开始监控 {package_name} (初始PID: {current_pid})")
    print(f"输出文件: {output_file}")
    print("输入 'q/quit/exit' 停止监控...")

    while not should_exit:
        with open(output_file, 'a') as f:
            # 写入时间戳标记
            f.write(f"\n\n===== 开始监控 PID {current_pid} @ {datetime.now()} =====\n")

            # 启动top进程
            process = subprocess.Popen(
                f"adb shell top -b -d 1 -p {current_pid}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
                bufsize=1,
                text=True
            )

            last_pid_seen = time.time()
            check_interval = 2  # 每2秒检查一次PID
            timeout = 5  # 5秒无PID视为进程死亡

            try:
                while not should_exit:
                    # 读取输出
                    line = process.stdout.readline()
                    if not line.strip():
                        time.sleep(0.1)
                        continue

                    # 写入输出文件
                    f.write(line)
                    f.flush()

                    # 检查输出中是否包含我们的PID
                    current_time = time.time()
                    if current_time - last_pid_seen > check_interval:
                        if str(current_pid) in line:
                            last_pid_seen = current_time
                        elif current_time - last_pid_seen > timeout:
                            print(f"\n[WARN] PID {current_pid} 已从top输出中消失")
                            break

                    # 检查进程是否意外终止
                    if process.poll() is not None:
                        print("\n[ERROR] top进程意外终止")
                        break

            except KeyboardInterrupt:
                should_exit = True
            except Exception as e:
                print(f"\n[ERROR] 监控出错: {e}")
            finally:
                cleanup()

        # 尝试获取新PID
        if not should_exit:
            print("\n尝试重新查找进程...")
            retry_count = 0
            max_retries = 9999
            retry_delay = 1

            while not should_exit and retry_count < max_retries:
                new_pid = get_pid(package_name)

                if new_pid and new_pid != current_pid and is_pid_alive(new_pid):
                    current_pid = new_pid
                    print(f"[INFO] 发现新PID: {current_pid}")
                    time.sleep(2)  # 等待进程稳定
                    break

                retry_count += 1
                print(f".", end="", flush=True)
                time.sleep(retry_delay)

            if retry_count >= max_retries:
                print("\n[ERROR] 无法找到运行中的进程，退出监控")
                should_exit = True

    print("\n监控已停止")

def main():
    if len(sys.argv) != 2:
        print("使用方法: python monitor_app.py <packageName>")
        print("示例: python monitor_app.py com.example.app")
        return

    package_name = sys.argv[1]

    # 检查adb是否可用
    try:
        subprocess.run("adb version", shell=True, check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("[ERROR] 未找到adb命令，请确保已安装Android SDK并配置环境变量")
        return

    print(f"正在查找 {package_name} 的进程...")
    initial_pid = get_pid(package_name)

    if not initial_pid:
        print(f"[ERROR] 未找到 {package_name} 的进程，请确保应用正在运行")
        return

    try:
        monitor_process(initial_pid, package_name)
    except Exception as e:
        print(f"[ERROR] 监控出错: {e}")
    finally:
        global should_exit
        should_exit = True

if __name__ == "__main__":
    main()