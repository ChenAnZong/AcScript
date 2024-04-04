import os, sys
import aiosqlite


class Sqlite3:
    # 放在
    db_file = "/www/wwwroot/43.224.152.122/data.db" if sys.platform != "win32" \
                  else os.path.join(os.path.dirname(__file__), '../sqlite', 'data.db')