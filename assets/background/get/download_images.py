import requests
from PIL import Image
import os
import re
import hashlib
from threading import Thread, active_count
from queue import Queue
import atexit
import logging
import time

# 设置日志配置
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"log_{int(time.time())}.log")
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 添加控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)

def calculate_md5(content):
    # 计算MD5哈希值
    md5_hash = hashlib.md5()
    md5_hash.update(content)
    return md5_hash.hexdigest()

def download_image(image_url, save_path, downloaded_hashes):
    try:
        # 发送HTTP请求下载图片
        response = requests.get(image_url)
        response.raise_for_status()  # 如果HTTP请求返回错误状态码，将引发异常

        # 计算图片的MD5哈希值
        md5_hash = calculate_md5(response.content)

        # 检查哈希值是否已经存在，如果是则调整count
        count = 1
        while md5_hash in downloaded_hashes:
            logging.warning(f"图片 {image_url} 已经下载过，调整文件名...")

            # 构造保存路径和文件名
            file_extension = response.headers.get('Content-Type').split('/')[-1]
            save_path = os.path.join(save_directory, f"{count}.{file_extension}")

            # 重新计算MD5哈希值
            md5_hash = calculate_md5(response.content + str(count).encode('utf-8'))
            count += 1

        # 保存图片到本地
        with open(save_path, 'wb') as file:
            file.write(response.content)

        # 添加已下载图片的哈希值到集合中
        downloaded_hashes.add(md5_hash)

        logging.info(f"图片 {image_url} 下载成功！")
    except Exception as e:
        logging.error(f"下载图片 {image_url} 失败：{str(e)}")

def convert_to_jpeg(image_path):
    try:
        # 打开图片文件
        with Image.open(image_path) as img:
            # 构造保存路径和文件名（转换为JPEG格式）
            save_path = os.path.splitext(image_path)[0] + '.jpg'

            # 转换并保存为JPEG格式
            img.convert('RGB').save(save_path, 'JPEG')

            logging.info(f"图片 {image_path} 转换为JPEG格式成功！")

        # 删除原始文件
        os.remove(image_path)
        logging.info(f"原始文件 {image_path} 删除成功！")

    except FileNotFoundError:
        logging.warning(f"文件 {image_path} 不存在，无法转换为JPEG格式。")

    except Exception as e:
        logging.error(f"转换图片 {image_path} 失败：{str(e)}")

def worker(queue, downloaded_hashes):
    while True:
        # 从队列中获取任务（图片URL和保存路径）
        image_url, save_path = queue.get()

        # 执行下载任务
        download_image(image_url, save_path, downloaded_hashes)

        # 转换为JPEG格式
        convert_to_jpeg(save_path)

        # 通知队列任务已完成
        queue.task_done()

# 注意，线程和起始图片数值在此设置
def download_images(api_url, save_directory):
    # 确保保存目录存在
    os.makedirs(save_directory, exist_ok=True)

    # 创建队列用于存放任务
    queue = Queue()

    # 获取系统的CPU核心数
    # 注意，二选一，第一个为自动配置，第二个为手动配置，请选择其一并注释掉另一个（使用#）
    # num_threads = min(os.cpu_count(), 1024)  # 限制最大线程数为1024，可根据需要调整
    num_threads = 128

    # 创建线程池
    threads = []
    downloaded_hashes = set()  # 存储已下载图片的哈希值
    for _ in range(num_threads):
        t = Thread(target=worker, args=(queue, downloaded_hashes))
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        # 发送HTTP请求获取图片列表
        response = requests.get(api_url, verify=True)
        response.raise_for_status()  # 如果HTTP请求返回错误状态码，将引发异常

        # 遍历图片列表，将下载任务添加到队列
        count = get_max_downloaded_number(save_directory) + 1
        while response.status_code == 200:
            # 获取文件扩展名
            file_extension = response.headers.get('Content-Type').split('/')[-1]

            # 构造保存路径和文件名
            save_path = os.path.join(save_directory, f"{count}.{file_extension}")

            # 将任务添加到队列
            queue.put((response.url, save_path))

            count += 1

            # 继续获取下一张图片
            response = requests.get(api_url, verify=True)

        # 阻塞直到队列中的所有任务完成
        queue.join()

    except requests.exceptions.RequestException as e:
        logging.error(f"发生异常: {e}")

    # 等待所有线程完成
    for t in threads:
        t.join()

    return save_directory  # 返回save_directory供atexit使用

def get_max_downloaded_number(save_directory):
    # 通过正则表达式找到已下载图片中的最大数字
    pattern = re.compile(r'(\d+)')
    existing_numbers = [int(pattern.search(filename).group()) for filename in os.listdir(save_directory) if pattern.search(filename)]
    return max(existing_numbers, default=0)

def clean_and_rename(save_directory):
    # 在程序退出时自动删除残留webq文件并自动重命名所有文件，顺序为数字顺序
    # 请注意，此处的实现可能需要根据您的需求进行调整
    webq_files = [f for f in os.listdir(save_directory) if f.endswith('.webq')]
    for webq_file in webq_files:
        webq_file_path = os.path.join(save_directory, webq_file)
        os.remove(webq_file_path)
        logging.info(f"删除残留的webq文件: {webq_file_path}")

    # 重命名所有文件，顺序为数字顺序
    files = [f for f in os.listdir(save_directory) if not f.endswith('.log')]
    files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    for i, file in enumerate(files, start=1):
        old_path = os.path.join(save_directory, file)
        new_path = os.path.join(save_directory, f"{i}.{file.split('.')[-1]}")
        os.rename(old_path, new_path)
        logging.info(f"文件重命名: {old_path} -> {new_path}")

if __name__ == "__main__":
    # API URL
    api_url = "https://t.mwm.moe/ycy"

    # 保存目录
    save_directory = r"D:\shengwang52005\shengwang52005.github.io\assets\background"

    # 调用函数下载图片
    save_directory = download_images(api_url, save_directory)

    # 在程序退出时自动清理和重命名
    atexit.register(clean_and_rename, save_directory)
