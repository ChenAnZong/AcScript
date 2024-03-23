import logging
import traceback
import json
import time
import asyncio
import glob
import os
import codecs
import sys
import aiofiles
from quart import request, Quart, json, send_file, redirect, abort, websocket, send_from_directory, make_response, \
    render_template, stream_with_context
from werkzeug.wsgi import FileWrapper
from typing import Dict

from quart_app_entry import ServerAPP

app = ServerAPP.app


# 校验请求是否合法 b85->md5 如果相等，则合法
@app.before_request
async def check_sign():
    pass


@app.route("/")
async def _index():
    return json.jsonify({
        "status": "成功",
        "platform": sys.platform,
        "pid": os.getpid()
    })

while True:
    logging.info(">>>>>>>>")
    ServerAPP.start()