import json
from collections import namedtuple
from abc import abstractmethod, ABC


class DbDataModel(ABC):
    @property
    @abstractmethod
    def _base_name_tuple(self):
        pass

    def __init__(self, *args):
        self.data = self._base_name_tuple(*args)

    def as_dict(self):
        return self._base_name_tuple._asdict(self.data)

    def __str__(self):
        return repr(self.data)

    @classmethod
    def create_from_db_rows(cls, rows):
        # 多行
        if isinstance(rows, list):
            l = []
            for i in rows:
                l.append(cls(*i))
            return l
        return cls(*rows)  # 单行


class ScriptTask(DbDataModel):
    """
    执行的脚本任务
    """

    @property
    def _base_name_tuple(self):
        return namedtuple('Project', ['id',
                                      'uuid',  # 任务唯一ID
                                      'date_create',  # 任务创建时间
                                      'date_update',  # 最近更新状态的时间
                                      'box_id',  # 盒子硬件ID
                                      'device_id',  # 执行的设备ID
                                      'script_project_id',  # 需要拉取执行的脚本ID
                                      'task_params_json',  # 脚本的执行参数, 发送到脚本的执行参数
                                      'timing_execute',  # 发送执行的时间戳
                                      'task_app',  # 目标APP
                                      'task_name',  # 任务名称
                                      'status_code',  # 当前状态码 <TaskStatus>
                                      'status_desc'])  # 当前状态描述

    def __init__(self, *args):
        super().__init__(*args)

    @classmethod
    def db_rows_to_task(cls, rows):
        # 多行
        if isinstance(rows, list):
            l = []
            for i in rows:
                l.append(cls(*i))
            return l
        return cls(*rows)  # 单行


class ScriptProject(DbDataModel):
    def __init__(self, *args):
        super().__init__(*args)

    @property
    def _base_name_tuple(self):
        return namedtuple('Project', ['id',
                                      'name',
                                      'date_create',
                                      'date_update',
                                      'author',
                                      'version_name',
                                      'update_count',
                                      'git_url',
                                      'zip_md5',
                                      'update_note_current',
                                      'manifest'])


class ResourceGroup(DbDataModel):
    def __init__(self, *args):
        super().__init__(*args)

    @property
    def _base_name_tuple(self):
        return namedtuple('ResourceGroup', ['id',
                                            'name',
                                            'type',
                                            'client_id',
                                            'date_create',
                                            'date_update',
                                            'tag'])


class ResourceData(DbDataModel):

    def __init__(self, *args):
        super().__init__(*args)

    @property
    def _base_name_tuple(self):
        return namedtuple('ResourceData',
                          ['id',
                           'group_id',
                           'data',
                           'used_count',
                           'date_last_used',
                           'note'])


class DbTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DbDataModel):
            obj: DbDataModel
            return obj.as_dict()
        else:
            kv_dict: dict = obj.__dict__
            return dict((key, value) for key, value in kv_dict.items() if
                        not callable(value) and not key.startswith('__'))


class ActionRet:
    def __init__(self, is_success: bool, desc: str):
        self.is_success = is_success
        self.desc = desc
        self.code = 0
        self.data = {}

    def to_json(self):
        return json.dumps(self, cls=DbTypeEncoder, ensure_ascii=False)
