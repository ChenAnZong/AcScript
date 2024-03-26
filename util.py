import hashlib
import time


def ts() -> int:
    return int(time.time())


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