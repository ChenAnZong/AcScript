import os
import aiosqlite

import util
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
            cur = await self.db.executemany(f"DELETE FROM Task WHERE id = ? ", [(c,) for c in task_uuid])
        else:
            cur = await self.db.execute(f"DELETE FROM Task WHERE uuid='{task_uuid}'")
        await self.db.commit()
        if cur.rowcount == 0:
            return ActionRet(False, f"未删除任何任务, 请确保任务ID正常")
        return ActionRet(True, f"成功删除任务, 条数:{cur.rowcount}")

    async def retry_task(self, task_uuid: Union[Tuple[str], str]) -> ActionRet:
        if isinstance(task_uuid, (list, tuple,)):
            cur = await self.db.executemany(
                f"UPDATE Task SET status_code = 1, status_desc = '等待重试', timing_execute = ? WHERE id = ? AND status_code != {TaskStatus.DEVICE_FINISH.value}",
                [(ts(), c,) for c in task_uuid])
        else:
            cur = await self.db.execute(
                f"UPDATE Task SET status_code = 1, status_desc = '等待重试', timing_execute = {ts()} WHERE uuid='{task_uuid}' AND status_code != {TaskStatus.DEVICE_FINISH.value};")
        await self.db.commit()
        if cur.rowcount == 0:
            return ActionRet(False, f"未查找到数据进行重试(为了排查问题可能是禁止重试, 请重新创建任务)")
        return ActionRet(True, f"修改任务重试, 条数:{cur.rowcount}")

    async def retry_task_pc_error(self, box_ids: Union[Tuple[str], str]) -> ActionRet:
        # 创建时间是15小时内 并且 预计执行的时间是已经超过了一个小时
        if isinstance(box_ids, (list, tuple,)):
            sql = f"UPDATE Task SET status_code = 1, status_desc = '等待重试(自动)', timing_execute = {ts()} WHERE status_code " \
                  f"NOT IN (1, 7, 9) AND date_create > {ts() - 72 * 60 * 60} AND timing_execute < {ts() - 60 * 60} AND " \
                  f"box_id = ?;"
            cur = await self.db.executemany(sql, [(c,) for c in box_ids])
        else:
            sql = f"UPDATE Task SET status_code = 1, status_desc = '等待重试(自动)', timing_execute = {ts()} WHERE status_code " \
                  f"NOT IN (1, 7, 9) AND date_create > {ts() - 72 * 60 * 60} AND timing_execute < {ts() - 60 * 60} " \
                  f"AND box_id = '{box_ids}';"
            cur = await self.db.execute(sql)
        await self.db.commit()
        if cur.rowcount == 0:
            return ActionRet(False, f"未查找到数据进行重试")
        return ActionRet(True, f"自动重试任务重试, 条数:{cur.rowcount}")

    async def create_task(self, req_json: dict) -> ActionRet:
        try:
            many_data = []
            if not isinstance(req_json, (list, tuple)):
                req_json = [req_json]
            for arr in req_json:
                many_data.append(
                    (str(uuid.uuid4()), ts(), ts(), arr["box_id"], arr["device_id"], arr["script_id"],
                     arr["task_app"], arr["task_name"], arr["param_json"], arr["timing_execute"],
                     TaskStatus.CREATED.value, '新建任务')
                )
            await self.db.executemany(
                "INSERT INTO Task (uuid, date_create, date_update, box_id, device_id, script_project_id, "
                "task_app, task_name, task_params_json, timing_execute, status_code, status_desc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(many_data))
            await self.db.commit()
            ret = ActionRet(True, "新建任务成功")
            ret.count = len(many_data)
            return ret
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                pass
            else:
                print("创建新卡数据库插入错误", repr(e))
            return ActionRet(False, f"新建项目失败, 错误原因: {repr(e)}")

    async def update_task_status(self, task_unique_id: str, status_code: int, status_desc: str) -> ActionRet:
        try:
            # 执行完成后不可再变更任务状态!
            sql = f"UPDATE Task SET status_code = ?, status_desc = ?, date_update = ? WHERE uuid = ? AND status_code != {TaskStatus.DEVICE_FINISH.value};"
            sql_args = (status_code, status_desc, ts(), task_unique_id)
            cur = await self.db.execute(sql, sql_args)
            await self.db.commit()
            if cur.rowcount == 0:
                return ActionRet(False, f"更新任务状态失败, 请确保任务ID正常")
            return ActionRet(True,
                             f"更新任务状态[{task_unique_id}]完成: {cur.rowcount} 当前服务器时间:{util.format_time()}")
        except Exception as e:
            return ActionRet(False, f"更新任务状态失败, 错误原因: {repr(e)}")

    async def query_all_task(self, box_ids: [str], per_page: int = 10, page_index: int = 1,
                             task_status_code: int = None,
                             device_id: str = None,
                             params: dict = {}):
        where_sql = ""
        GET_WHERE_PREFIX = lambda: " AND " if where_sql else " WHERE"

        # 处理前端的查询提交参数 -----
        if "status_desc" in params:
            task_status_code = int(params.get("status_desc"))
            del params["status_desc"]
        for (k, v) in params.items():
            where_sql += f"{GET_WHERE_PREFIX()} {k} = '{v}'"

        # 指定任务类型筛选
        if task_status_code is not None:
            where_sql = f"WHERE status_code={task_status_code}"
        # 指定设备ID筛选
        if device_id is not None:
            where_sql += f"{GET_WHERE_PREFIX()} device_id={device_id}"
        where_sql += GET_WHERE_PREFIX()
        where_sql += f"""({' OR '.join([f'box_id = "{i}"' for i in box_ids])})"""

        sql = f"SELECT * FROM Task {where_sql} ORDER BY date_update DESC LIMIT {int(per_page)} " \
              f"OFFSET {(int(page_index) - 1) * (int(per_page))};"

        cur: Cursor = await self.db.execute(sql)
        alr = await cur.fetchall()
        print("查询", sql)
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
        """
        一个机位最大拉取4个任务同时!
        :param box_id:
        :return:
        """
        limit_len = 4 if len(box_id) > 10 else 300
        cur: Cursor = await self.db.execute(
            f"SELECT * FROM Task WHERE box_id='{box_id}' AND status_code={TaskStatus.CREATED.value} "
            f"AND timing_execute < {ts()} ORDER BY timing_execute DESC LIMIT {limit_len};"
        )
        f = await cur.fetchall()
        return ScriptTask.db_rows_to_task(f)


if __name__ == "__main__":
    print(TaskStatus.CREATED.value)
    sql = f"UPDATE Task SET status_code = 1, status_desc = '等待重试', timing_execute = {ts()} WHERE status_code " \
          f"NOT IN (1, 7, 9) AND date_create > {ts() - 48 * 60 * 60} AND timing_execute < {ts() - 60 * 60} AND " \
          f"box_id = '8b37cb73da77e931e94b8d37aac0599d'"
    print(sql)
