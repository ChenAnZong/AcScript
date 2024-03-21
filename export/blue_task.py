from quart import request, Quart, Blueprint, json, send_file, redirect, abort, websocket, send_from_directory, \
    make_response, \
    render_template, stream_with_context
from data import ScriptTaskManager

task = Blueprint("task", import_name=__name__, url_prefix="/task")
task_manager = ScriptTaskManager()


# 请求地址为 http://127.0.0.1:5031/task/create
@task.route("/create", methods=["POST"])
async def _create_task():
    req_json = await request.get_json()
    return json.jsonify(task_manager.create_task(
        device_id=req_json["device_id"],
        project_id=req_json["project_id"],
        script_project_id=req_json["script_id"],
        param_json=req_json["param_json"],
        timing_execute=req_json["timing_execute"]
    ))


@task.route("/delete", methods=["POST"])
async def _delete_task():
    req_json = await request.get_json()
    return json.jsonify(task_manager.delete_task(
        task_uuid=req_json["task_unique_id"]  # 可以为数组, 或者字符串均可
    ))


@task.route("/query", methods=["POST"])
async def _query_task():
    req_json = await request.get_json()
    return json.jsonify(task_manager.query_all_task(
        per_page=req_json["per_page"],
        page_index=req_json["page_index"],
        task_status_code=req_json.get("task_status_code"),  # 如果提交了此参数则指定
        device_id=req_json.get("device_id")  # 如果提交了此参数则指定
    ))


@task.route("/update_status", methods=["POST"])
async def _update_status():
    req_json = await request.get_json()
    return json.jsonify(task_manager.update_task_status(
        task_unique_id=req_json["task_unique_id"],
        status_code=req_json["status_code"],
        status_desc=req_json["status_desc"]
    ))
