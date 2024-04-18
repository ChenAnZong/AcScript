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


class ProjectManager:
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
                await self.db.execute(f"UPDATE Project SET update_count = update_count + 1 WHERE id={project_id};")
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
        return ScriptProject.create_from_db_rows(alr)

    async def query_one_project(self, project_id: int) -> ScriptProject:
        sql = f"SELECT * FROM Project WHERE id={project_id};"
        cur: Cursor = await self.db.execute(sql)
        o = await cur.fetchone()
        return ScriptProject.create_from_db_rows(o)

    async def update_manifest(self, project_id: int, manifest: str) -> ActionRet:
        try:
            sql = f"UPDATE Project SET date_update = ?, manifest = ? WHERE id={project_id};"
            cur = await self.db.execute(sql, (ts(), manifest,))
            await self.db.commit()
            return ActionRet(True, f"更新{cur.rowcount}条项目数据")
        except Exception as e:
            return ActionRet(False, f"更新项目摘要错误: {repr(e)}")
