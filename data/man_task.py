import os
import aiosqlite
from data.model import ActionRet, ScriptTask, ScriptProject
from data.model_type import TaskStatus
from data.db_loader import Sqlite3
from typing import Union, Tuple
import asyncio
import uuid
import sys
from aiosqlite.cursor import Cursor
from util import ts


class ScriptTaskManager:
    def __init__(self):
        asyncio.get_event_loop().run_until_complete(self.init())

    async def init(self):
        self.db = await aiosqlite.connect(
            Sqlite3.db_file,
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

    async def query_all_task(self, box_ids: [str], per_page: int = 10, page_index: int = 1, task_status_code: int = None,
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

        if "WHERE" not in where_sql:
            where_sql += " WHERE "
        else:
            where_sql += " AND "
        where_sql += f"""({' OR '.join([f'box_id = "{i}"' for i in box_ids])})"""

        sql = f"SELECT * FROM Task {where_sql} ORDER BY date_update DESC LIMIT {int(per_page)} " \
              f"OFFSET {(int(page_index) - 1) * (int(per_page))};"

        cur: Cursor = await self.db.execute(sql)
        alr = await cur.fetchall()
        # print("查询", sql)
        sql_query_count = f"SELECT COUNT(*) AS total FROM Task {where_sql};"
        cur: Cursor = await self.db.execute(sql_query_count)
        ct = await cur.fetchone()
        # print("查询条数:", ct)
        return (ScriptTask.db_rows_to_task(alr), ct[0])

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


if __name__ == "__main__":
    print(TaskStatus.CREATED.value)
