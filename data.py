import os
import aiosqlite
from collections import namedtuple
from model import ActionRet
import time
from enum import Enum
from typing import Union, Tuple
import asyncio
import uuid
from aiosqlite.cursor import Cursor
from util import ts


class TaskStatus(Enum):
    """
    执行的任务状态
    """
    # 刚新建状态
    CREATED = 1
    # 已向设备推送执行指令
    PC_HAS_SEND = 3
    # 手机正在执行中
    DEVICE_EXE = 5
    # 手机执行完成
    DEVICE_FINISH = 7
    # 手机执行异常
    DEVICE_EXE_ERROR = 9


class ScriptTask:
    """
    执行的脚本任务
    """
    # 下面这些字段跟数据库的列键名一模一样的
    _base_task = namedtuple('Project', ['id',
                                        'uuid',         # 任务唯一ID
                                        'task_name',    # 任务名称
                                        'date_create',  # 任务创建时间
                                        'date_update',  # 最近更新状态的时间
                                        'device_id',    # 执行的设备ID
                                        'script_project_id',    # 需要拉取执行的脚本ID
                                        'task_params_json',     # 脚本的执行参数, 发送到脚本的执行参数
                                        'timing_execute',       # 发送执行的时间戳
                                        'status_code',          # 当前状态码 <TaskStatus>
                                        'status_desc'])         # 当前状态描述

    def __init__(self, *args):
        self.project = ScriptTask._base_task(*args)

    @staticmethod
    def db_rows_to_task(rows):
        # 多行
        if isinstance(rows, list):
            l = []
            for i in rows:
                l.append(ScriptTask(*i))
            return l
        return ScriptTask(*rows)  # 单行


class ScriptTaskManager:
    def __init__(self):
        asyncio.get_event_loop().run_until_complete(self.init())

    async def init(self):
        self.db = await aiosqlite.connect(
            os.path.join(os.path.dirname(__file__), 'sqlite', 'data.db'),
            timeout=20,
            check_same_thread=True)
        self.db.text_factory = lambda b: b.decode(errors='ignore')
        self.cur = await self.db.cursor()
        await self.create_table()

    async def create_table(self):
        sqlite_create_table_query = '''CREATE TABLE Task (
                                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                                      uuid TEXT NOT NULL UNIQUE,
                                      date_create TINYINT NOT NULL,
                                      date_update TEXT NOT NULL,
                                      device_id TEXT NOT NULL,
                                      script_project_id INTEGER NOT NULL,
                                      update_count INTEGER,
                                      task_params_json TEXT NOT NULL,
                                      timing_execute TEXT,
                                      status_code TINYINT,
                                      status_desc TEXT
                                      );'''
        try:
            print("初始化新表")
            await self.db.execute(sqlite_create_table_query)
            await self.db.commit()
        except aiosqlite.OperationalError as _:
            pass

    async def delete_task(self, task_uuid: Union[Tuple[str], str]) -> ActionRet:
        if isinstance(task_uuid, (list, tuple,)):
            cur = await self.db.executemany(f"DELETE FROM Task WHERE code = ? ", [(c,) for c in task_uuid])
        else:
            cur = await self.db.execute(f"DELETE FROM Task WHERE code='{task_uuid}'")
        await self.db.commit()
        return ActionRet(True, f"成功删除任务, 条数:{cur.rowcount}")

    async def create_task(self, device_id: str, project_id: str, script_project_id: int, param_json: str, timing_execute: str) -> ActionRet:
        try:
            unique_id = str(uuid.uuid4())
            await self.db.execute(
                f"INSERT INTO Task (uuid, date_create, date_update, device_id, script_project_id, task_params_json, timing_execute, status_code, status_desc)  VALUES "
                f"('{unique_id}', '{ts()}', '{ts()}', '{device_id}','{project_id}','{script_project_id}', '{timing_execute}', '{TaskStatus.CREATED.value}', '新建任务');"
            )
            return ActionRet(True, "新建任务成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def update_task_status(self, task_unique_id: str, status_code: int, status_desc: str) -> ActionRet:
        try:
            sql = f"UPDATE Task SET status_code = ?, status_desc = ?, date_update = ?" \
                  f"WHERE uuid={task_unique_id}; "
            sql_args = (status_code, status_desc, ts(), task_unique_id)
            await self.db.execute(sql, sql_args)
            return ActionRet(True, "更新任务状态成功")
        except Exception as e:
            return ActionRet(False, f"更新任务状态失败, 错误原因: {repr(e)}")

    async def query_all_task(self, per_page: int = 10, page_index: int = 1, task_status_code: int = None, device_id: str = None):
        where_sql = ""
        # 指定任务类型筛选
        if task_status_code is not None:
            where_sql = f"WHERE status_code={task_status_code}"
        # 指定设备ID筛选
        if device_id is None:
            if where_sql:
                where_sql += f" AND device_id={device_id}"
            else:
                where_sql = f"WHERE device_id={device_id}"

        sql = f"SELECT * FROM Task ORDER BY date_update DESC LIMIT {int(per_page)} " \
              f"OFFSET {(int(page_index) - 1) * (int(per_page))} {where_sql};"
        cur: Cursor = await self.db.execute(sql)
        alr = await cur.fetchall()
        return ScriptTask.db_rows_to_task(alr)

    async def get_task_params(self, task_unique_id: str) -> str:
        a = await self.db.execute(
            f"SELECT task_params_json FROM Task WHERE uuid='{task_unique_id}';"
        )
        return (await a.fetchone())[0]

    async def fetch_device_task(self, device_id: str) -> ScriptTask:
        # 选择一条创建的任务
        a = await self.db.execute(
            f"SELECT * FROM Task WHERE device_id='{device_id}' AND status_code={TaskStatus.PC_HAS_SEND} ORDER BY timing_execute DESC LIMIT 1;"
        )
        f = await a.fetchone()[0]
        return ScriptTask.db_rows_to_task(f)


###################################


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


class ProjectManager:
    def __init__(self):
        asyncio.get_event_loop().run_until_complete(asyncio.gather(self.init()))
        pass

    async def init(self):
        self.db = await aiosqlite.connect(
            os.path.join(os.path.dirname(__file__), 'sqlite', 'data.db'),
            timeout=20,
            check_same_thread=True)
        self.db.text_factory = lambda b: b.decode(errors='ignore')
        self.cur = await self.db.cursor()
        await self.create_table()

    async def create_table(self):
        sqlite_create_table_query = '''CREATE TABLE Project (
                                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     name TEXT NOT NULL UNIQUE,
                                     date_create TEXT NOT NULL,
                                     date_update TEXT,
                                     author TEXT NOT NULL,
                                     version_name TEXT,
                                     update_count INTEGER,
                                     git_url TEXT,
                                     zip_md5 TEXT,
                                     update_note_current TEXT
                                     );'''
        try:
            await self.db.execute(sqlite_create_table_query)
            await self.db.commit()
        except aiosqlite.OperationalError as _:
            pass

    async def create_project(self, project_name: str, project_author: str, project_git_url: str) -> ActionRet:
        try:
            await self.db.execute(
                f"INSERT INTO Project (name, date_create, author, git_url, update_count)  VALUES "
                f"('{project_name}', '{ts()}', '{project_author}', '{project_git_url}', 0);"
            )
            return ActionRet(True, "新建项目成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def update_project(self, project_id: int, md5: str, has_zip_change: bool, version_name: str, git_url: str, update_note: str) -> ActionRet:
        try:
            if has_zip_change:
                sql = f"UPDATE Project SET date_update = ?, version_name = ?, git_url = ?, zip_md5 = ?" \
                      f"update_note_current = ? WHERE id={project_id}; "
                sql_args = (ts(), version_name, git_url, md5, update_note)
                await self.db.execute("UPDATE Project SET update_count = update_count + 1;")
            else:
                sql = f"UPDATE Project SET date_update = ?, version_name = ?, git_url = ?" \
                      f"update_note_current = ? WHERE id={project_id}; "
                sql_args = (ts(), version_name, git_url, update_note,)
            await self.db.execute(sql, sql_args)
            return ActionRet(True, "更新项目成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def delete_project(self, project_id:int) -> ActionRet:
        try:
            sql = f"DELETE FROM Project Where id={project_id};"
            cur = await self.db.execute(sql)
            return ActionRet(True, f"删除{cur.rowcount}条项目数据")
        except Exception as e:
            return ActionRet(False, f"删除项目错误: {repr(e)}")

    async def query_all_project(self, per_page:int= 10, page_index:int=1):
        sql = f"SELECT * FROM Project ORDER BY date_update DESC LIMIT {int(per_page)} " \
              f"OFFSET {(int(page_index) - 1) * (int(per_page))};"
        cur: Cursor = await self.db.execute(sql)
        alr = await cur.fetchall()
        return ScriptProject.db_rows_to_project(alr)


if __name__ == "__main__":
    print(TaskStatus.CREATED.value)