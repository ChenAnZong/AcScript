import hashlib
import time


def ts() -> int:
    return int(time.time())


def format_time():
    """
    获取格式化的时间, 格式样式如:2024.02.04 12:56:31
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def md5_file(path) -> str:
    """
    对文件进行md5摘要计算, 检查文件是否完整
    :param path:
    :return:
    """
    md5 = hashlib.md5()
    f = open(path, mode="rb")
    md5.update(f.read())
    f.close()
    md5_sum = md5.hexdigest()
    return md5_sum.lower()