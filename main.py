import logging
import traceback
import json
import time
import os
import sys
from quart import request, Quart, json, send_file, redirect, abort, websocket, send_from_directory, make_response, \
    render_template, stream_with_context
from werkzeug.wsgi import FileWrapper
from typing import Dict
import psutil
from quart_app_entry import ServerAPP

app = ServerAPP.app
st = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 校验请求是否合法 b85->md5 如果相等，则合法
@app.before_request
async def check_sign():
    pass


@app.route("/status")
async def _status():
    return json.jsonify({
        "status": "成功",
        "platform": sys.platform,
        "pid": os.getpid(),
        "start_time": st,
        "cpu": psutil.cpu_percent(interval=1, percpu=True),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage("/")
    })


@app.route("/<path>")
async def _index(path):
    return await render_template("index.html")

while True:
    logging.info(">>>>>>>>")
    ServerAPP.start()