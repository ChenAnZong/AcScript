import traceback

import aiosqlite
from typing import Union, Tuple
import asyncio
from data.model import ActionRet, ResourceData, ResourceGroup
from data.db_loader import Sqlite3
from aiosqlite.cursor import Cursor
from util import ts


class ResourceManager:
    def __init__(self):
        asyncio.get_event_loop().run_until_complete(asyncio.gather(self.init()))
        pass

    async def init(self):
        self.db = await aiosqlite.connect(
            Sqlite3.db_file,
            timeout=20,
            check_same_thread=True)
        self.db.text_factory = lambda b: b.decode(errors='ignore')
        self.cur = await self.db.cursor()
        await self.create_table()

    async def create_table(self):
        sqlite_create_res_group = '''CREATE TABLE res_group (
                                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                                     name TEXT NOT NULL,
                                     type TINYINT NOT NULL,
                                     client_id TEXT NOT NULL,
                                     date_create INTEGER NOT NULL,
                                     date_update INTEGER,
                                     count INTEGER,
                                     tag TEXT
                                     );'''

        sqlite_create_res_data = '''CREATE TABLE res_data (
                                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                                         group_id INTEGER NOT NULL,
                                         data TEXT NOT NULL,
                                         used_count INTEGER NOT NULL,
                                         date_last_used INTEGER,
                                         note TEXT
                                         );'''
        try:
            await self.db.execute("""
CREATE TRIGGER IF NOT EXISTS update_res_group_count
AFTER DELETE ON res_data
BEGIN
    UPDATE res_group
    SET count = (
        SELECT COUNT(*)
        FROM res_data
        WHERE group_id = OLD.group_id
    )
    WHERE id = OLD.group_id;
END;
            """)
            await self.db.execute(sqlite_create_res_group)
            await self.db.execute(sqlite_create_res_data)
            await self.db.commit()
        except aiosqlite.OperationalError as _:
            pass

    async def create_group(self, req_json: dict) -> ActionRet:
        try:
            client_id = req_json["client_id"]
            res_name = req_json["resource_name"]
            res_type = req_json["resource_type"]
            res_tag = req_json["resource_tag"]
            ts_v = ts()
            await self.db.execute(
                f"INSERT INTO res_group (name, type, client_id, date_create, date_update, tag) VALUES "
                f"(?, ?, ?, ?, ?, ?);"
                , (res_name, res_type, client_id, ts_v, ts_v, res_tag,))
            await self.db.commit()
            cur: Cursor = await self.db.execute("SELECT * FROM res_group WHERE date_create = ?", (ts_v,))
            row = await cur.fetchone()
            ret = ActionRet(True, f"新建资源组{res_name}成功")
            print("转换数据:", row, ResourceGroup.create_from_db_rows(row))
            ret.data = ResourceGroup.create_from_db_rows(row)
            return ret
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                return ActionRet(False, f"重复创建了")
            else:
                print("数据库插入错误", repr(e))
            return ActionRet(False, f"新建失败, 错误原因: {repr(e)}")

    async def update_data(self, req_json: dict) -> ActionRet:
        try:
            group_id = int(req_json["group_id"])
            data = req_json["data"]
            ld = tuple([(group_id, d["content"], 0, 0, d["note"]) for d in data])
            await self.db.executemany(
                f"INSERT INTO res_data (group_id, data, used_count, date_last_used, note) VALUES "
                f"(?, ?, ?, ?, ?);", ld)
            await self._update_group_count(group_id)
            await self.db.commit()
            ret = ActionRet(True, f"上传资源数据成功, 共{len(ld)}条")
            return ret
        except aiosqlite.IntegrityError as e:
            if "UNIQUE constraint failed" in repr(e):
                return ActionRet(False, f"Key重复")
            else:
                print("数据库插入错误", repr(e))
            return ActionRet(False, f"错误原因: {repr(e)}")

    async def _update_group_count(self, group_id:int):
        sql = f"""
UPDATE res_group
SET count = (
    SELECT COUNT(*)
    FROM res_data
    WHERE group_id = {group_id}
)
WHERE id = {group_id};
"""
        await self.db.execute(sql)

    async def query_group(self, req_json: dict) -> ActionRet:
        try:
            client_id = req_json["client_id"]
            per_page = req_json["per_page"]  # 每页多少个行
            page_index = int(req_json["page_index"])  # 当前第几页, 从1开始
            res_type = int(req_json.get("res_type", 0))  # 资源类型 0 未指定, 全部类型
            res_type_sql = "" if res_type == 0 else f" AND type = {res_type}"
            if page_index < 1:
                page_index = 1
            sql = f"SELECT * FROM res_group WHERE client_id = '{client_id}' {res_type_sql} ORDER BY date_create DESC, date_update DESC " \
                  f"LIMIT {int(per_page)} " \
                  f"OFFSET {(int(page_index) - 1) * (int(per_page))};"
            print(sql)
            cur: Cursor = await self.db.execute(sql)
            alr = await cur.fetchall()
            ret = ActionRet(True, f"查询成功, 共{len(list(alr))}条")
            ret.data = ResourceGroup.create_from_db_rows(alr)

            sql_query_count = f"SELECT COUNT(*) FROM res_group WHERE client_id = '{client_id}';"
            cur: Cursor = await self.db.execute(sql_query_count)
            ct = await cur.fetchone()
            ret.total = ct[0]

            return ret
        except Exception as e:
            return ActionRet(False, f"查询失败, 错误原因: {traceback.format_exc()}")

    async def query_data(self, req_json: dict) -> ActionRet:
        try:
            print(req_json)
            group_id = req_json["group_id"]  # 每页多少个行
            per_page = req_json["per_page"]  # 每页多少个行
            page_index = int(req_json["page_index"])  # 当前第几页, 从1开始
            like_data = req_json.get("match_data", None)
            like_note = req_json.get("match_note", None)
            # sort_by = req_json.get("sort_by", "date_last_used")
            # sort_type = req_json.get("sort_type", "DESC")
            like_sql = ""
            if like_data is not None:
                like_sql += f"AND data LIKE '%{like_data}%' "
            if like_note is not None:
                like_sql += f"AND note LIKE '%{like_note}%' "

            if page_index < 1:
                page_index = 1
            sql = f"SELECT * FROM res_data WHERE group_id = {group_id} {like_sql} ORDER BY date_last_used DESC, used_count " \
                  f"LIMIT {int(per_page)} " \
                  f"OFFSET {(int(page_index) - 1) * (int(per_page))};"
            print(sql)
            cur: Cursor = await self.db.execute(sql)
            alr = await cur.fetchall()
            ret = ActionRet(True, f"查询成功, 共{len(list(alr))}条")
            ret.data = ResourceData.create_from_db_rows(alr)
            ret.count = len(list(alr))

            sql_query_count = f"SELECT COUNT(*) FROM res_data WHERE group_id = {group_id} {like_sql};"
            cur: Cursor = await self.db.execute(sql_query_count)
            ct = await cur.fetchone()
            ret.total = ct[0]
            return ret
        except Exception as e:
            return ActionRet(False, f"查询失败, 错误原因: {repr(e)}")

    async def fetch_data(self, req_json: dict) -> ActionRet:
        try:
            group_id = req_json["group_id"]  # 每页多少个行
            count = req_json["count"]  # 每页多少个行
            sql = f"SELECT * FROM res_data WHERE group_id = {group_id} ORDER BY date_last_used, used_count " \
                  f"LIMIT {int(count)};"
            cur: Cursor = await self.db.execute(sql)
            alr = await cur.fetchall()
            ret = ActionRet(True, f"查询成功, 共{len(list(alr))}条")
            ret.data = ResourceData.create_from_db_rows(alr)
            return ret
        except Exception as e:
            return ActionRet(False, f"查询失败, 错误原因: {repr(e)}")

    async def update_used_count(self, req_json: dict) -> ActionRet:
        try:
            uld = tuple([(d["count"], d["id"]) for d in req_json])
            sql = "UPDATE res_data SET used_count = ?  WHERE id = ?;"
            cur: Cursor = await self.db.executemany(sql, uld)
            await self.db.commit()
            ret = ActionRet(True, f"修改成功, 共{cur.rowcount}条")
            ret.count = cur.rowcount
            return ret
        except Exception as e:
            return ActionRet(False, f"查询失败, 错误原因: {repr(e)}")

    async def update_data_note(self, req_json: dict) -> ActionRet:
        try:
            uld = tuple([([d["note"], int(d["id"])]) for d in req_json])
            sql = "UPDATE res_data SET note = ?  WHERE id = ?;"
            cur: Cursor = await self.db.executemany(sql, uld)
            await self.db.commit()
            ret = ActionRet(True, f"修改成功, 共{cur.rowcount}条")
            return ret
        except Exception as e:
            return ActionRet(False, f"查询失败, 错误原因: {repr(e)}")

    async def delete_data(self, req_json):
        try:
            uld = [(i,) for i in req_json["ids"]]
            print(uld)
            sql = f"DELETE FROM res_data WHERE id=?;"
            cur: Cursor = await self.db.executemany(sql, uld)
            await self.db.commit()
            ret = ActionRet(True, f"删除成功, 共{cur.rowcount}条数据")
            return ret
        except Exception as e:
            return ActionRet(False, f"删除成功, 错误原因: {traceback.format_exc()}")

    async def delete_group(self, req_json):
        try:
            uld = [(i,) for i in req_json["ids"]]
            print("提交", uld)
            sql1 = f"DELETE FROM res_group WHERE id = ?;"
            sql2 = f"DELETE FROM res_data WHERE group_id = ?;"
            cur1: Cursor = await self.db.executemany(sql1, uld)
            cur2: Cursor = await self.db.executemany(sql2, uld)
            await self.db.commit()
            ret = ActionRet(True, f"删除成功, 共{cur1.rowcount}个分组")
            return ret
        except Exception as e:
            return ActionRet(False, f"删除成功, 错误原因: {repr(e)}")