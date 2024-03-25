import json
from enum import Enum
import requests
import codecs
import sys


def get_device_id() -> str:
    """
    获取手机的设备ID
    :return:
    """
    if sys.platform != "win32":
        id_path = "/data/local/tmp/.id"
        with codecs.open(id_path, mode="r") as fr:
            return fr.read()
    else:
        # 可以使用这个来进行测试
        return "b9d95d3a69df76dbe7622db892f12fd676828622426efba3ac483e80631011de"


class TaskStatus(Enum):
    # 手机正在执行中
    DEVICE_EXE = 5
    # 手机执行完成
    DEVICE_FINISH = 7
    # 手机执行异常
    DEVICE_EXE_ERROR = 9


class Task:
    SERVER_BASE_URL = "http://127.0.0.1:5031"

    def __init__(self):
        ret_json = requests.get(f"{Task.SERVER_BASE_URL}/task/fetch_device_task?device_id={get_device_id()}").json()
        # print(ret_json)
        # 输出例子如下, 我们脚本只关心运行参数与uuid:
        # {
        #     "id": 3,
        #     "uuid": "5b2088cb-7f08-4003-b61e-87e068c88876",
        #     "date_create": 1711246437,
        #     "date_update": 1711246437,
        #     "box_id": "42ed7bb33e47e1d9a7edb6d6bf5cd200",
        #     "device_id": "b9d95d3a69df76dbe7622db892f12fd676828622426efba3ac483e80631011de",
        #     "script_project_id": 5,
        #     "task_params_json": " {\"aaaa\":6}",
        #     "timing_execute": "1711243885",
        #     "task_app": "抖音",
        #     "task_name": "发布视频",
        #     "status_code": 3,
        #     "status_desc": "新建任务"
        # }
        self.ret_json = ret_json
        self.task_id = ret_json["uuid"]
        self.params_json = ret_json["task_params_json"]
        self.params = json.loads(self.params_json)
        self.update_task_status(TaskStatus.DEVICE_EXE, "手机成功拉取任务参数")

    def update_task_status(self, st: TaskStatus, desc: str):
        rj = {
            "task_unique_id": self.task_id,
            "status_code": st.value,
            "status_desc": desc
        }
        print(requests.post(f"{self.SERVER_BASE_URL}/task/update_status?device_id={get_device_id()}", json=rj).text)

    def __str__(self):
        return str(self.ret_json)


if __name__ == "__main__":
    task = Task()
    print("成功获取到运行参数")
    print("正在运行脚本....", task.params)    # 输出 正在运行脚本.... {'aaaa': 6}

    # 如果脚本运行异常
    task.update_task_status(TaskStatus.DEVICE_EXE_ERROR, "执行错误, 抖音账号未登录")

    # 如果代码错误, 也可以上报, 虽然前端不好看, 先排查问题再说
    try:
        a = 1 / 0
    except Exception as e:
        task.update_task_status(TaskStatus.DEVICE_EXE_ERROR, f"代码错误: {repr(e)}")

    # 如果脚本正常运行完毕
    task.update_task_status(TaskStatus.DEVICE_FINISH, "执行完成")

