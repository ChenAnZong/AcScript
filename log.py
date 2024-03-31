import logging
from logging.handlers import RotatingFileHandler


class CustomFormatter(logging.Formatter):
    """Logging colored formatter, adapted from https://stackoverflow.com/a/56944256/3638629"""

    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Logger:
    logger = logging.getLogger("DEFAULT")
    logging.basicConfig(level=logging.INFO, datefmt='%a, %d %b %Y %H:%M:%S',
                        format='%(asctime)s-行%(lineno)d|线%(thread)d ⇛ %(message)s')  # logging.basicConfig函数对日志的输出格式及方式做相关配置
    logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler("server.log", mode='a', maxBytes=100 * 1024 * 1024, backupCount=1,
                                       encoding="utf-8",
                                       delay=True)

    file_handler.setFormatter(logging.Formatter("%(asctime)s-[%(lineno)d] - %(message)s"))
    logger.addHandler(file_handler)
    fmt = '%(asctime)s | %(levelname)1s | %(message)s'
    stdout_handler.setFormatter(CustomFormatter(fmt))
    logger.addHandler(stdout_handler)


server_logger = Logger.logger
