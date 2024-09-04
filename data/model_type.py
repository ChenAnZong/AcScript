from enum import Enum


# 资源类型
class ResourceType(Enum):
    TEXT = 1
    IMAGE = 2
    VIDEO = 3


# 状态类型
class TaskStatus(Enum):
    """
    以下常量值 需要使用复制即可; 如果新增状态, 不会修改已有的数字值
    """
    #  任务新建
    CREATED = 1
    #  推送异常
    PC_SEND_ERROR = 2
    #  等待机位
    WAIT_SLOT = 21
    #  正在开机
    WAIT_BOOT = 22
    #  开机错误
    BOOR_ERROR = 221
    #  等待环境
    WAIT_ENV = 23
    #  等待环境超时
    WAIT_ENV_TIME_OUT = 24
    #  代理配置异常
    PROXY_ERROR = 25
    #  等待机位空闲
    PC_WAIT_SLOT = 26
    #  已向设备推送执行指令
    PC_HAS_SEND = 3
    #  脚本正在执行中
    DEVICE_EXE = 5
    #  脚本执行完成
    DEVICE_FINISH = 7
    #  脚本执行异常
    DEVICE_EXE_ERROR = 9

if __name__ == "__main__":
    print(TaskStatus.CREATED.value)