import os
import json
from quart import request, Quart, Blueprint, send_file, redirect, abort, websocket, send_from_directory, \
    make_response, \
    render_template, stream_with_context, Response
from data import ProjectManager
from model import ActionRet, DbTypeEncoder
from util import md5_file, ts
from log import Logger

project = Blueprint("project", import_name=__name__, url_prefix="/project")
project_man = ProjectManager()
loger = Logger.logger


# [前端]此处后面返回前端的网页index.html; 请求地址为 http://127.0.0.1:5031/project/
@project.route("/", methods=["GET"])
async def _index():
    return ts()


# [前端]请求地址为 http://127.0.0.1:5031/project/create
@project.route("/create", methods=["POST"])
async def _create_project():
    """
    新建脚本工程
    :return:
    """
    req_json = await request.get_json()
    name = req_json["name"]  # 此名字后期不可更改
    author = req_json["author"]
    git_url = req_json["git_url"]
    ret = await project_man.create_project(name, author, git_url)
    return ret.to_json()


# [前端]删除工程
@project.route("/delete", methods=["POST"])
async def _delete_project():
    """
    删除脚本工程
    :return:
    """
    req_json = await request.get_json()
    name = req_json["project_id"]  # 此名字后期不可更改
    ret = await project_man.delete_project(name)
    return ret.to_json()


# [前端]按页列出所有工程
@project.route("/list", methods=["POST"])
async def _list_project():
    """
    列出当前所有脚本工程
    :return:
    """
    req_json = await request.get_json()
    per_page = req_json["per_page"]
    page_index = req_json["page_index"]
    try:
        ret = await project_man.query_all_project(per_page, page_index)
        print("查询返回:", ret)
        return json.dumps(ret, cls=DbTypeEncoder)
    except Exception as e:
        print(repr(e))
        loger.error("查询工程错误", stack_info=True)
        return json.dumps([])


# [PC]
@project.route("/project_info", methods=["GET"])
async def _project_info():
    project_id = int(request.args.get("id"))
    return json.dumps(await project_man.query_one_project(project_id))


# [前端]
@project.route("/update", methods=["POST"])
async def _update_project():
    """
    脚本工程上传更新
    :return:
    """
    form = await request.form
    # 如果这些字段都没有发生变化, 则拉取原来的值即可, 不能不提交
    # 工程ID
    project_id = form["project_id"]
    # Git链接
    git_url = form["git_url"]
    # 更新说明
    update_note = form["update_note"]
    # 版本名称
    update_version = form["update_version"]
    # 提交的Zip文件工程包, 如果没有更新变化, 不要提交此字段
    md5 = None
    if "zip" in request.files:
        project_zip = request.files["zip"]
        # 保存在服务器project_zip目录下 文件名为 <md5>.zip
        local_file = f"project_zip/{project_zip.filename}.zip"
        project_zip.save(local_file)
        md5 = md5_file(local_file)
        os.rename(project_zip, md5 + ".zip")
    ret = await project_man.update_project(project_id, md5, md5 is not None, update_version, git_url, update_note)
    return ret.to_json()


# [前端/PC]下载工程的链接如 http://127.0.0.1:5031/project/download?id=1
@project.route("/download", methods=["GET"])
async def _download_project():
    """
    此接口主要供PC下载脚本工程发送到手机执行, 前端也可以进行点击下载
    :return:
    """
    project_id = request.args.get("id")
    local = os.path.join("../project_zip", project_id + ".zip")
    if os.path.exists(local):
        return await send_file(local, as_attachment=True)
    else:
        return Response(response="文件不存在", status=400)


if __name__ == "__main__":
    print(ActionRet(True, "成功").to_json())