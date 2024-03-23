import logging
import json
from quart import request, Quart, Blueprint, send_file, redirect, abort, websocket, send_from_directory, \
    make_response, \
    Response
from data import ScriptTaskManager, ActionRet
from model import DbTypeEncoder

task = Blueprint("task", import_name=__name__, url_prefix="/task")
task_manager = ScriptTaskManager()


# [前端]请求地址为 http://127.0.0.1:5031/task/create
@task.route("/create", methods=["POST"])
async def _create_task():
    req_json = await request.get_json()
    ret: ActionRet = await task_manager.create_task(
        box_id=req_json["box_id"],                  # 盒子硬件ID
        device_id=req_json["device_id"],            # 安卓设备ID
        task_app=req_json["task_app"],              # 任务app, 如抖音, 小红书, Tiktok
        task_name=req_json["task_name"],            # 如更改头像, 发布视频
        script_project_id=req_json["script_id"],    # 脚本工程ID
        param_json=req_json["param_json"],
        timing_execute=req_json["timing_execute"]
    )
    return ret.to_json()


# [前端]删除任务
@task.route("/delete", methods=["POST"])
async def _delete_task():
    req_json = await request.get_json()
    ret = await task_manager.delete_task(
        task_uuid=req_json["task_unique_id"]  # 可以为数组, 或者字符串均可
    )
    return ret.to_json()


# [待用]查询任务的具体参数, 这个暂时用不上
@task.route("/task_params", methods=["GET"])
async def _params_from_task():
    return await task_manager.get_task_params(request.args["task_unique_id"])


# [手机]手机的工程被运行, 向服务器拉取任务信息, 服务器会自动选择一条适合执行的任务
@task.route("/fetch_device_task", methods=["GET"])
async def _fetch_task():
    try:
        device_id = request.args.get("device_id")  # 在手机上脚本通过 shell("cat /data/local/tmp/.id") 进行读取
        r = await task_manager.fetch_device_task(device_id)
        return json.dumps(r, cls=DbTypeEncoder)
    except Exception as e:
        return Response(f"获取错误: {repr(e)}", status=501)


# [PC]软件查询工程任务, 前端不用看这个接口
@task.route("/fetch_pc_task", methods=["GET"])
async def _distb_task():
    try:
        device_id = request.args.get("box_id")  # 在手机上脚本通过 shell("cat /data/local/tmp/.id") 进行读取
        r = await task_manager.fetch_pc_task(device_id)
        return json.dumps(r, cls=DbTypeEncoder)
    except Exception as e:
        logging.error("获取PC任务", stack_info=True)
        return Response(f"获取错误: {repr(e)}", status=501)


# [前端]查询所有任务
@task.route("/query", methods=["POST"])
async def _query_task():
    req_json = await request.get_json()
    ret_task = await task_manager.query_all_task(
        per_page=req_json["per_page"],
        page_index=req_json["page_index"],
        task_status_code=req_json.get("task_status_code"),  # 如果提交了此参数则指定
        device_id=req_json.get("device_id")  # 如果提交了此参数则指定
    )
    return json.dumps(ret_task, cls=DbTypeEncoder)


# [前端/PC/手机]脚本运行完毕后, 请求这个接口更新任务状态
@task.route("/update_status", methods=["POST"])
async def _update_status():
    req_json = await request.get_json()
    ret:ActionRet = await task_manager.update_task_status(
        task_unique_id=req_json["task_unique_id"],
        status_code=req_json["status_code"],
        status_desc=req_json["status_desc"]
    )
    return ret.to_json()
