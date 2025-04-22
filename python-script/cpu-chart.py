import matplotlib.pyplot as plt
import re
import sys


# 定义读取文件并提取时间和CPU数据的函数
def read_cpu_data(file_path):
    times = []
    cpu_values = []

    with open(file_path, "r") as file:
        counter = 0
        for line in file:
            # 使用正则表达式提取时间和CPU数据
            match = re.search(r"^ *\d+ .*S +(\d*[.]\d*)", line)
            if match:
                counter+= 1
                time = counter
                cpu_value = float(match.group(1))
                times.append(time)
                cpu_values.append(cpu_value)
                print(f"Time: {time}, CPU Usage: {cpu_value}")

    return times, cpu_values


# 定义绘制折线图的函数
def plot_cpu_data(times, cpu_values):
    plt.figure(figsize=(10, 5))
    plt.plot(times, cpu_values, marker="o", linestyle="-", color="b")
    plt.xlabel("Time")
    plt.ylabel("CPU Usage (%)")
    plt.title("CPU Usage Over Time")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# 主函数
def main():
    file_path = sys.argv[1]
    times, cpu_values = read_cpu_data(file_path)
    plot_cpu_data(times, cpu_values)


if __name__ == "__main__":
    main()