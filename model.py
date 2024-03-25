import json
from collections import namedtuple
from enum import Enum


def convert_namedtuple_to_dict(nt):
    return nt._asdict()


class TaskStatus(Enum):
    """
    以下常量值 需要使用复制即可; 如果新增状态, 不会修改已有的数字值
    """
    #  任务新建
    CREATED = 1,
    #  推送异常
    PC_SEND_ERROR = 2,
    #  等待机位
    WAIT_SLOT = 21,
    #  正在开机
    WAIT_BOOT = 22,
    #  开机错误
    BOOR_ERROR = 221,
    #  等待环境
    WAIT_ENV = 23,
    #  等待环境超时
    WAIT_ENV_TIME_OUT = 24,
    #  代理配置异常
    PROXY_ERROR = 25,
    #  等待机位空闲
    PC_WAIT_SLOT = 26,
    #  已向设备推送执行指令
    PC_HAS_SEND = 3,
    #  脚本正在执行中
    DEVICE_EXE = 5,
    #  脚本执行完成
    DEVICE_FINISH = 7,
    #  脚本执行异常
    DEVICE_EXE_ERROR = 9


class ScriptTask:
    """
    执行的脚本任务
    """
    # 下面这些字段跟数据库的列键名一模一样的
    _base_task = namedtuple('Project', ['id',
                                        'uuid',         # 任务唯一ID
                                        'date_create',  # 任务创建时间
                                        'date_update',  # 最近更新状态的时间
                                        'box_id',       # 盒子硬件ID
                                        'device_id',    # 执行的设备ID
                                        'script_project_id',    # 需要拉取执行的脚本ID
                                        'task_params_json',     # 脚本的执行参数, 发送到脚本的执行参数
                                        'timing_execute',       # 发送执行的时间戳
                                        'task_app',             # 目标APP
                                        'task_name',            # 任务名称
                                        'status_code',          # 当前状态码 <TaskStatus>
                                        'status_desc'])         # 当前状态描述

    def __init__(self, *args):
        self.task = ScriptTask._base_task(*args)

    @staticmethod
    def db_rows_to_task(rows):
        # 多行
        if isinstance(rows, list):
            l = []
            for i in rows:
                l.append(ScriptTask(*i))
            return l
        return ScriptTask(*rows)  # 单行


class ScriptProject:
    # 下面这些字段跟数据库的列键名一模一样的
    _base_project = namedtuple('Project', ['id',
                                           'name',
                                           'date_create',
                                           'date_update',
                                           'author',
                                           'version_name',
                                           'update_count',
                                           'git_url',
                                           'zip_md5',
                                           'update_note_current'])

    def __init__(self, *args):
        self.project = ScriptProject._base_project(*args)

    @staticmethod
    def db_rows_to_project(rows):
        # 多行
        if isinstance(rows, list):
            l = []
            for i in rows:
                l.append(ScriptProject(*i))
            return l
        return ScriptProject(*rows)  # 单行


class DbTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ScriptProject):
            obj: ScriptProject
            return convert_namedtuple_to_dict(obj.project)
        if isinstance(obj, ScriptTask):
            obj: ScriptTask
            return convert_namedtuple_to_dict(obj.task)
        return super(DbTypeEncoder, self).default(obj)


class ActionRetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ActionRet):
            return {'is_success': obj.is_success, 'desc': obj.desc}
        return super(ActionRetEncoder, self).default(obj)


class ActionRet:
    def __init__(self, is_success: bool, desc: str):
        self.is_success = is_success
        self.desc = desc

    def to_json(self):
        return json.dumps(self, cls=ActionRetEncoder, ensure_ascii=False)
