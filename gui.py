import tkinter as tk
from tkinter import filedialog, scrolledtext
import down
import threading
import queue as queue_module
import os
import sys
import random


class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass


def start_download_process():
    global download_path  # 声明 download_path 为全局变量
    # 将路径中的正斜杠替换为双反斜杠
    formatted_download_path = download_path.replace('/', '\\\\')
    # 显示获取的信息，实际应用中这里将调用下载函数
    print("Download Path:", formatted_download_path)
    message_queue = queue_module.Queue()  # 使用别名来创建Queue实例
    # Redirect output
    sys.stdout = RedirectText(output_area)
    # 启动下载线程
    threading.Thread(target=download_thread, args=(formatted_download_path, message_queue), daemon=True).start()
    # 定期检查队列
    check_queue(message_queue)


def check_queue(queue):
    while not queue.empty():
        message = queue.get()
        output_area.insert(tk.END, message)
        output_area.see(tk.END)
    # 100毫秒后再次检查队列
    root.after(100, check_queue, queue)

def download_thread(path, queue):
    # 这个函数将在单独的线程中运行
    if not os.path.exists(path):
        os.makedirs(path)
    try:
        down.main(path)  # 假设 down.main 接受一个参数
        queue.put("Download completed successfully.\n")
    except Exception as e:
        queue.put(str(e) + "\n")


def select_download_path():
    global download_path
    download_path = filedialog.askdirectory()
    # download_file = filedialog.askopenfilename()
    path_label.config(text=f"Download Path: {download_path}")


# 创建图形化界面
root = tk.Tk()
root.title("文献下载1.4")

# 创建标签、输入框和按钮
path_label = tk.Label(root, text="Download Path: Not selected")
space_label1 = tk.Label(root, text="")  # 空白标签用于添加空行
path_button = tk.Button(root, text="Select Path", command=select_download_path)
space_label2 = tk.Label(root, text="")  # 第二个空白标签用于添加空行
start_button = tk.Button(root, text="Start Download", command=start_download_process)


# 布置界面元素
space_label1.pack()  # 第一个空行
path_label.pack()
path_button.pack()
space_label2.pack()  # 第三个空行
start_button.pack()

# Create ScrolledText widget
output_area = scrolledtext.ScrolledText(root)
output_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
# Redirect output to the GUI
sys.stdout = RedirectText(output_area)

# 全局变量存储下载路径
download_path = ""

root.geometry('500x500')
# 运行界面的主循环
root.mainloop()
