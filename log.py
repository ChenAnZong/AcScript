import logging


class Logger:
    logger = logging.getLogger()
    logging.basicConfig(level=logging.INFO, datefmt='%a, %d %b %Y %H:%M:%S',
                        format='%(asctime)s-行%(lineno)d|线%(thread)d ⇛ %(message)s')  # logging.basicConfig函数对日志的输出格式及方式做相关配置
    logger.setLevel(logging.DEBUG)