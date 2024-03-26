import os
import aiosqlite
from model import ActionRet, ScriptTask, ScriptProject, TaskStatus
from typing import Union, Tuple
import asyncio
import uuid
from aiosqlite.cursor import Cursor
from util import ts


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
                                      date_create INTEGER NOT NULL,
                                      date_update INTEGER NOT NULL,
                                      box_id TEXT NOT NULL,
                                      device_id TEXT NOT NULL,
                                      script_project_id INTEGER NOT NULL,
                                      task_params_json TEXT NOT NULL,
                                      timing_execute INTEGER TEXT,
                                      task_app TEXT,
                                      task_name TEXT,
                                      status_code TINYINT,
                                      status_desc TEXT
                                      );'''
        try:
            await self.db.execute(sqlite_create_table_query)
            await self.db.commit()
        except aiosqlite.OperationalError as _:
            pass

    async def delete_task(self, task_uuid: Union[Tuple[str], str]) -> ActionRet:
        if isinstance(task_uuid, (list, tuple,)):
            cur = await self.db.executemany(f"DELETE FROM Task WHERE uuid = ? ", [(c,) for c in task_uuid])
        else:
            cur = await self.db.execute(f"DELETE FROM Task WHERE uuid='{task_uuid}'")
        await self.db.commit()
        if cur.rowcount == 0:
            return ActionRet(False, f"未删除任何任务, 请确保任务ID正常")
        return ActionRet(True, f"成功删除任务, 条数:{cur.rowcount}")

    async def create_task(self, box_id: str, device_id: str, script_project_id: int,
                          task_app: str, task_name: str,
                          param_json: str, timing_execute: str) -> ActionRet:
        try:
            unique_id = str(uuid.uuid4())
            await self.db.execute(
                "INSERT INTO Task (uuid, date_create, date_update, box_id, device_id, script_project_id, "
                "task_app, task_name, task_params_json, timing_execute, status_code, status_desc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (unique_id, ts(), ts(), box_id, device_id, script_project_id,
                 task_app, task_name, param_json, timing_execute, TaskStatus.CREATED.value, '新建任务')
            )
            await self.db.commit()
            return ActionRet(True, "新建任务成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def update_task_status(self, task_unique_id: str, status_code: int, status_desc: str) -> ActionRet:
        try:
            sql = f"UPDATE Task SET status_code = ?, status_desc = ?, date_update = ? WHERE uuid = ?;"
            sql_args = (status_code, status_desc, ts(), task_unique_id)
            cur = await self.db.execute(sql, sql_args)
            await self.db.commit()
            if cur.rowcount == 0:
                return ActionRet(False, f"更新任务状态失败, 请确保任务ID正常")
            return ActionRet(True, f"更新任务状态完成: {cur.rowcount}")
        except Exception as e:
            return ActionRet(False, f"更新任务状态失败, 错误原因: {repr(e)}")

    async def query_all_task(self, per_page: int = 10, page_index: int = 1, task_status_code: int = None,
                             device_id: str = None):
        where_sql = ""
        # 指定任务类型筛选
        if task_status_code is not None:
            where_sql = f"WHERE status_code={task_status_code}"
        # 指定设备ID筛选
        if device_id is not None:
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

    async def fetch_device_task(self, device_id: str) -> Union[ScriptTask, None]:
        # 选择一条创建的任务
        a = await self.db.execute(
            f"SELECT * FROM Task WHERE device_id='{device_id}' AND status_code={TaskStatus.PC_HAS_SEND.value} ORDER BY timing_execute DESC LIMIT 1;"
        )
        f = await a.fetchone()
        if f is None:
            return None
        return ScriptTask.db_rows_to_task(f)

    async def fetch_pc_task(self, box_id: str) -> ScriptTask:
        cur: Cursor = await self.db.execute(
            f"SELECT * FROM Task WHERE box_id='{box_id}' AND status_code={TaskStatus.CREATED.value} "
            f"AND timing_execute < {ts()} ORDER BY timing_execute DESC;"
        )
        f = await cur.fetchall()
        return ScriptTask.db_rows_to_task(f)


###################################


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
                                     date_create INTEGER NOT NULL,
                                     date_update INTEGER,
                                     author TEXT NOT NULL,
                                     version_name TEXT,
                                     update_count INTEGER,
                                     git_url TEXT,
                                     zip_md5 TEXT,
                                     update_note_current TEXT,
                                     manifest TEXT,
                                     );'''
        try:
            await self.db.execute(sqlite_create_table_query)
            await self.db.commit()
        except aiosqlite.OperationalError as _:
            pass

    async def create_project(self, project_name: str, project_author: str, project_git_url: str) -> ActionRet:
        try:
            await self.db.execute(
                f"INSERT INTO Project (name, date_create, author, git_url, update_count) VALUES "
                f"('{project_name}', {ts()}, '{project_author}', '{project_git_url}', 0);"
            )
            await self.db.commit()
            return ActionRet(True, "新建项目成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                return ActionRet(True, f"脚本名字重复了: {project_name}")
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def update_project(self, project_id: int, md5: str, has_zip_change: bool, version_name: str, git_url: str,
                             update_note: str) -> ActionRet:
        try:
            if has_zip_change:
                sql = f"UPDATE Project SET date_update = ?, version_name = ?, git_url = ?, zip_md5 = ? ," \
                      f"update_note_current = ? WHERE id={project_id};"
                sql_args = (ts(), version_name, git_url, md5, update_note)
                await self.db.execute("UPDATE Project SET update_count = update_count + 1;")
            else:
                sql = f"UPDATE Project SET date_update = ?, version_name = ?, git_url = ? ," \
                      f"update_note_current = ? WHERE id={project_id}; "
                sql_args = (ts(), version_name, git_url, update_note,)
            await self.db.execute(sql, sql_args)
            await self.db.commit()
            return ActionRet(True, "更新项目成功")
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def delete_project(self, project_id: int) -> ActionRet:
        try:
            sql = f"DELETE FROM Project Where id={project_id};"
            cur = await self.db.execute(sql)
            await self.db.commit()
            return ActionRet(True, f"删除{cur.rowcount}条项目数据")
        except Exception as e:
            return ActionRet(False, f"删除项目错误: {repr(e)}")

    async def query_all_project(self, per_page: int = 10, page_index: int = 1):
        if page_index < 1:
            page_index = 1
        sql = f"SELECT * FROM Project ORDER BY date_update DESC, date_create DESC LIMIT {int(per_page)} " \
              f"OFFSET {(int(page_index) - 1) * (int(per_page))};"
        cur: Cursor = await self.db.execute(sql)
        alr = await cur.fetchall()
        return ScriptProject.db_rows_to_project(alr)

    async def query_one_project(self, project_id: int) -> ScriptProject:
        sql = f"SELECT * FROM Project WHERE id={project_id};"
        cur: Cursor = await self.db.execute(sql)
        o = await cur.fetchone()
        return ScriptProject.db_rows_to_project(o)

    async def update_manifest(self, project_id:int, manifest: str) -> ActionRet:
        try:
            sql = f"UPDATE Project SET date_update = ?, manifest = ? WHERE id={project_id};"
            cur = await self.db.execute(sql, (ts(), manifest, ))
            await self.db.commit()
            return ActionRet(True, f"更新{cur.rowcount}条项目数据")
        except Exception as e:
            return ActionRet(False, f"更新项目摘要错误: {repr(e)}")


if __name__ == "__main__":
    print(TaskStatus.CREATED.value)
