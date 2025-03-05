import requests
from bs4 import BeautifulSoup
import os
import psutil
import threading
import time
import re
import random

# 请求头
head = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
}

# 统计变量
total_papers = 0
successful_downloads = 0
failed_downloads = 0

# 记录开始时间
start_time = time.time()

# 全局变量控制监控线程
monitoring_active = True


# 提取 DI 号并保存到初步文件
def extract_numbers(input_file_path, output_file_path):
    with open(input_file_path, 'r', encoding='utf-8', errors='ignore') as input_file:
        content = input_file.read()

    titles = re.findall(r'TI (.+?)(?=SO|$)', content, re.DOTALL)
    journals = re.findall(r'SO (.+?)(?=\n|$)', content, re.DOTALL)
    di_numbers = re.findall(r'DI (.+?)(?=\n|$)', content, re.DOTALL)

    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for title, journal, di_number in zip(titles, journals, di_numbers):
            formatted_title = re.sub(r"\s+", " ", title.strip())
            formatted_journal = re.sub(r"\s+", " ", journal.strip())
            formatted_di_number = re.sub(r"\s+", " ", di_number.strip())
            output_file.write(f"题目名: {formatted_title}\n")
            output_file.write(f"期刊名: {formatted_journal}\n")
            output_file.write(f"DOI号: {formatted_di_number}\n\n")

    print("信息提取完成，并已保存到 " + output_file_path)


# 提取 DI 号并保存到最后一步文件
def extract_di_numbers(input_file_path, output_file_path):
    di_numbers = []
    with open(input_file_path, 'r', encoding='utf-8', errors='ignore') as input_file:
        for line in input_file:
            if line.startswith("DOI号: "):
                di_number = line.strip().split(' ')[1]
                di_numbers.append(di_number)

    with open(output_file_path, 'w') as output_file:
        for di_number in di_numbers:
            output_file.write(di_number + '\n')

    print("DI 号提取完成，并已保存到 " + output_file_path)


# 下载文献的函数
def download_paper(doi, title, path, paper_counter):
    global successful_downloads, failed_downloads
    file_name = f"{paper_counter}-{title}.pdf"
    url = "https://www.wellesu.com/" + doi + "#"
    try:
        download_url = ""
        time.sleep(random.uniform(1, 2))  # 随机等待 5 到 10 秒
        proxies = {'http': None, 'https': None}  # 禁用代理
        r = requests.get(url, headers=head, proxies=proxies)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        if soup.iframe is None:
            download_url = soup.embed.attrs["src"]
        else:
            download_url = soup.iframe.attrs["src"]

        download_r = requests.get(download_url, headers=head, proxies=proxies)  # 同样禁用代理
        download_r.raise_for_status()

        # 保存文献
        with open(path + file_name, "wb") as temp:
            temp.write(download_r.content)

        print(doi + "\t文献下载成功.\n")
        successful_downloads += 1
        time.sleep(2)  # 等待一段时间，避免请求过于频繁

    except Exception as e:
        with open(path + "error.log", "a+") as error:
            error.write(doi + "\t下载失败!\n")
            error.write(str(e) + "\n\n")
        print(doi + "\t文献下载失败.\n")
        failed_downloads += 1


def clean_title(title):
    return re.sub(r'[\\/*?:"<>|]', '', title)  # 清理文件名中的非法字符


# 资源监控函数
def monitor_resource_usage():
    global monitoring_active
    while monitoring_active:
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        print(f"CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%")

        if cpu_usage > 80 or memory_usage > 80:
            print("Resource usage is high, adjusting...")
            # 需要时添加资源调整代码
            time.sleep(10)

        time.sleep(5)


# 主函数
def main(download_path):
    global total_papers, successful_downloads, failed_downloads, monitoring_active, paper_counter, lock

    # 创建papers文件夹用于保存文献
    path = download_path.replace("\\", "/")
    if not path.endswith("/"):
        path += "/"

    if not os.path.exists(path):
        os.mkdir(path)

    # 启动资源监控线程
    monitor_thread = threading.Thread(target=monitor_resource_usage)
    monitor_thread.start()

    total_papers = 0
    successful_downloads = 0
    failed_downloads = 0
    paper_counter = 1
    lock = threading.Lock()  # 创建一个锁对象

    # 调用提取 DI 号的函数
    extract_numbers(path + "savedrecs.txt", path + "doi_first.txt")
    extract_di_numbers(path + "doi_first.txt", path + "doi.txt")

    with open(path + "doi_first.txt", "r", encoding="utf-8") as f:
        threads = []
        title = ""
        for line in f:
            if line.startswith("题目名: "):
                title = line.replace("题目名: ", "").strip()
                title = clean_title(title)
            elif line.startswith("DOI号: "):
                with lock:  # 在修改 paper_counter 之前获取锁
                    doi = line.replace("DOI号: ", "").strip()
                    total_papers += 1
                    t = threading.Thread(target=download_paper, args=(doi, title, path, paper_counter))
                    paper_counter += 1  # 更新 paper_counter
                threads.append(t)
                title = ""  # 重置标题为下一个条目准备

        # 启动所有线程
        for t in threads:
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

    # 记录结束时间
    end_time = time.time()
    elapsed_time = end_time - start_time

    # 打印统计信息
    print("总共文献数: ", total_papers)
    print("成功下载文献数: ", successful_downloads)
    print("下载失败文献数: ", failed_downloads)
    print("总共用时: ", elapsed_time, "秒")

    # 在主程序结束时停止资源监控
    monitoring_active = False
    monitor_thread.join()  # 等待资源监控线程结束


if __name__ == "__main__":
    main("path_to_your_directory")  # 需要替换为您的实际路径
