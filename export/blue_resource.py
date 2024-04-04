from quart import request, Blueprint, render_template
from data.man_resource import ResourceManager

res = Blueprint("resource", import_name=__name__, url_prefix="/res", static_folder="../dist/assets")
res_man = ResourceManager()


@res.route("/")
async def _index():
    return await render_template("index.html")


# 创建资源分组
@res.route("/create_group", methods=["POST"])
async def _create():
    req_json = await request.form
    ret = await res_man.create_group(req_json)
    return ret.to_json()


# 上传资源
@res.route("/upload", methods=["POST"])
async def _upload():
    req_json = await request.get_json()
    ret = await res_man.update_data(req_json)
    return ret.to_json()


# 更新资源使用信息
@res.route("/update_used_count", methods=["POST"])
async def _update_used_count():
    req_json = await request.get_json()
    ret = await res_man.update_used_count(req_json)
    return ret.to_json()


@res.route("/fetch", methods=["GET"])
async def _fetch():
    ret = await res_man.fetch_data(request.args)
    return ret.to_json()


@res.route("/query_group", methods=["GET"])
async def _query_group():
    req_json = request.args
    ret = await res_man.query_group(req_json)
    return ret.to_json()


@res.route("/query_data", methods=["GET"])
async def _query_data():
    req_json = request.args
    ret = await res_man.query_data(req_json)
    return ret.to_json()


@res.route("/note_data", methods=["POST"])
async def _note_data():
    req_json = await request.get_json()
    ret = await res_man.update_data_note(req_json)
    return ret.to_json()


# 删除资源
@res.route("/delete_data", methods=["POST"])
async def _delete_data():
    req_json = await request.get_json()
    ret = await res_man.delete_data(req_json)
    return ret.to_json()


@res.route("/delete_group", methods=["POST"])
async def _delete_group():
    req_json = await request.get_json()
    ret = await res_man.delete_group(req_json)
    return ret.to_json()

