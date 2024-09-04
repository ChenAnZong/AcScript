import codecs
import logging
import traceback
import json
import time
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import aiofiles
from quart import request, Response, Quart, json, send_file, redirect, abort, websocket, send_from_directory, make_response, \
    render_template, stream_with_context
from quart.datastructures import FileStorage
import psutil
import sys
import util
from other.mail_outlook import fetch_tk_code_and_verify, handle_check_email
executor = ThreadPoolExecutor()

process_pid = set()
process_pid.add(os.getpid())


async def run_blocking_task(func, *args):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, func, *args)
    return result


def daemonize():
    pid = os.fork()
    if pid:
        print("退出启动进程")
        os._exit(0)
    os.umask(0)
    os.setsid()
    pid2 = os.fork()
    if pid2:
        print("守护进程启动成功： PID={}".format(os.getpid()))
        # 守护进程，判断进程是否挂掉
        while True:
            time.sleep(10)
            if psutil.pid_exists(pid2):
                continue
            else:
                print("观察到工作进程已死亡，重启进程！~")
                reboot_application()
                exit()
    else:
        process_pid.add(os.getppid())
        process_pid.add(os.getpid())
        print("工作进程启动完成！！DAEMON PPID={} PID={}".format(os.getppid(), os.getpid()))

    sys.stdout.flush()
    sys.stderr.flush()

    with open('/dev/null') as read_null, open('/dev/null', 'w') as write_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())
    print("开始执行工作代码")


def clean():
    """
    清理之前的所有python进程与浏览器进程
    """
    py_process_name = os.path.basename(sys.executable)
    py_code_file_name = os.path.basename(__file__)
    print(f"当前运行: {py_process_name} {py_code_file_name}")
    for p in psutil.process_iter():
        # kill another me
        try:
            process_cmdline = p.cmdline()
            if not p.cmdline():
                continue
        except psutil.ZombieProcess:
            continue
        if "python" in str(process_cmdline):
            print("发现其它python进程:" + str(process_cmdline))
            if py_process_name in str(process_cmdline) and py_code_file_name in str(process_cmdline):
                if p.pid not in process_pid:
                    p.kill()
                    print("已有启动中的实例，结束： " + str(p))
                else:
                    print("当前python进程：" + str(p))


if sys.platform != "win32":
    clean()
    if len(sys.argv) < 2:
        daemonize()


from quart_app_entry import ServerAPP
app = ServerAPP.app
st = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 校验请求是否合法 b85->md5 如果相等，则合法
@app.before_request
async def check_sign():
    pass


@app.after_request
async def process_res(r):
    r: Response
    # r.headers.add("Server-Version", "2024.3")
    r.headers.add("Access-Control-Allow-Origin", "*")
    r.headers.add("Access-Control-Allow-Credentials", "true")
    r.headers.add("Access-Control-Allow-Private-Network", "true")
    # r.headers.add("Access-Control-Max-Age", str(1728000))
    # r.headers.add("Cache-Control", "no-cache")
    # r.headers.add("Access-Control-Allow-Methods", "GET,HEAD,OPTIONS,POST,PUT")
    # r.headers.add("Access-Control-Allow-Headers",
    #   "DNT,X-CustomHeader,Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type")
    return r


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


@app.route("/task_manage")
async def _index_task():
    # logging.info("URL" + request.url)
    return await render_template("index.html")


@app.route("/resource_manage")
async def _index_res():
    return await render_template("index.html")


@app.route("/project_manage")
async def _index_project():
    return await render_template("index.html")


@app.route("/proxy", methods=["GET"])
async def _proxy():
    cmd = "nohup /usr/local/bin/proxy --hostname 0.0.0.0 --basic-auth juzhen:yyds --port 8081&"
    is_running = False
    ret = ""
    for p in psutil.process_iter():
        if "local/bin/proxy" in str(p.cmdline()):
            is_running = True
            ret += f"exe: {p.exe()} cmdline: {p.cmdline()} status: {p.status()} create_time: {p.create_time()}<br>"
    if not is_running:
        ret = str(os.system(cmd))
    return ret


@app.route("/time", methods=["GET"])
async def _time():
    cmd = "nohup /usr/local/bin/proxy --hostname 0.0.0.0 --basic-auth juzhen:yyds --port 8081&"
    is_running = False
    ret = ""
    for p in psutil.process_iter():
        if "local/bin/proxy" in str(p.cmdline()):
            is_running = True
            ret += f"exe: {p.exe()} cmdline: {p.cmdline()} status: {p.status()} create_time: {p.create_time()}<br>"
    if not is_running:
        ret = str(os.system(cmd))
    return ret


@app.route("/update-dist", methods=["POST"])
async def _post_file():
    """
    服务器接收文件并写出
    :return:
    """
    file = (await request.files)['file']
    print("Update-dist-file-archive:" + file.filename)
    await file.save(file.filename)
    extract_to = r"dist"
    import shutil
    shutil.rmtree(extract_to, ignore_errors=True)
    shutil.unpack_archive(file.filename, extract_to)
    os.remove(file.filename)
    return file.filename


@app.route("/ip", methods=["GET"])
async def _ip():
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    print("启动程序#日志打印：", loggers)
    return str(request.remote_addr)


@app.route("/theb", methods=["GET"])
async def _theb_js():
    async with aiofiles.open("thebai.js", mode="r+") as fr:
        return await fr.read()


@app.route("/pc_log_report", methods=["POST"])
async def _pc_log_report():
    form = await request.form
    files = await request.files
    log_file_name = f"{util.format_time().replace(':', '-')}_{form['pc_code']}_{form['login_user']}_{form['os_version'].replace(' ', '#')}_{form['client_version']}_{form['cpu_name'].replace(' ', '')}.zip"
    log_zip_fs: FileStorage = files.get("log_zip")
    # print("文件名:", log_file_name)
    # print("文件1:", files.get("log_zip"))
    # 目录不存在则创建目录
    if not os.path.exists("report"):
        os.mkdir("report")
    await log_zip_fs.save(destination=os.path.join("report", log_file_name))
    # f.get()
    # 返回成功的话客户端就删除日志
    return "上报success|" + log_file_name


@app.route("/tk_outlook", methods=["POST"])
async def _tk_outlook():
    # 在主线程中调用异步函数来执行阻塞的同步调用
    try:
        rj = await request.get_json()
        u = rj["username"]
        p = rj["password"]
        result = await asyncio.wait_for(fut=run_blocking_task(fetch_tk_code_and_verify, u, p), timeout=60)
    except asyncio.TimeoutError:
        result = "登录获取超时"
    except Exception as e:
        async with aiofiles.open("tk_error.log", mode="a+") as fw:
            await fw.write(repr(e) + "\n")
            await fw.write(traceback.format_exc() + "\n")
            await fw.flush()
        result = traceback.format_exc()
    return result


@app.route("/email_check", methods=["POST"])
async def _tk_email_check():
    # 在主线程中调用异步函数来执行阻塞的同步调用
    try:
        rj = await request.get_json()
        et = rj["emails_text"]
        result = await asyncio.wait_for(fut=run_blocking_task(handle_check_email, et), timeout=10*60)
    except asyncio.TimeoutError:
        result = "检测超时"
    except Exception as e:
        async with aiofiles.open("tk_error.log", mode="a+") as fw:
            await fw.write(repr(e) + "\n")
            await fw.write(traceback.format_exc() + "\n")
            await fw.flush()
        result = traceback.format_exc()
    return result


@app.errorhandler(404)
def error_handler_404(error):
    app.logger.error(f"请求404出错: {request.url} {request.headers.get('User-Agent, ''')}")
    return redirect("/ip")


@app.errorhandler(500)
def error_handler_500(error):
    app.logger.error(f"请求500出错: {request.url} {error}")
    return "服务器500出错\请联系开发者处理\ TEL:13066312388\n" + str(error), 500


def reboot_application():
    new_pid = os.spawnv(os.P_NOWAITO, sys.executable, sys.argv[1:])
    print("马上重启进程，当前进程pid={} 新进程pid={}".format(os.getgid(), new_pid))
    exit(0)


while True:
    print(">>>>>>>> {0}".format(sys.argv))
    ServerAPP.start()