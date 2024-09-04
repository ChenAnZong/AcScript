import sys, os

import quart.logging
from quart import Quart
from quart_cors import cors
from export.blue_project import project as blueprint_project
from export.blue_task import task as blueprint_task
from export.blue_resource import res as blueprint_resource
import logging
from log import MyLogger


class Config:
    IS_DEBUG = sys.platform == "win32"


class ServerAPP:
    cfg = Config()
    cors_settings = {
        "allow_methods": ["POST", "GET"], "allow_origin": ["http://127.0.0.1:5031", "http://43.224.152.122:5031"], "allow_credentials": True,
        "allow_headers": "Content-Type"
    }
    from quart.logging import default_handler
    print(logging.root.manager.loggerDict)
    # logging.getLogger('quart.app').removeHandler(default_handler)
    app = Quart(__name__, static_folder=r'dist/assets', template_folder='dist')
    app.register_blueprint(blueprint=cors(blueprint_project, **cors_settings))
    app.register_blueprint(blueprint=cors(blueprint_task, **cors_settings))
    app.register_blueprint(blueprint=cors(blueprint_resource, **cors_settings))
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 64
    app = cors(app, **cors_settings)

    @classmethod
    def start(cls):
        if cls.cfg.IS_DEBUG:
            MyLogger.setup(cls.app.logger)
            MyLogger.setup(logging.getLogger("hypercorn.access"))
            MyLogger.setup(logging.getLogger("hypercorn.error"))
            loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
            print("启动程序#日志打印：", loggers)
            cls.app.run(host="0.0.0.0", port=5031, debug=True)
        else:
            import asyncio
            from hypercorn.config import Config
            from hypercorn.asyncio import serve

            # config = Config()
            # config._bind = ["0.0.0.0:5031"]
            # config.keep_alive_timeout = 0.0
            # config.shutdown_timeout = 0.0
            ServerAPP.app.logger.setLevel(logging.DEBUG)
            # asyncio.run(serve(cls.app, config))
            os.system("unset http_proxy")
            os.system("unset https_proxy")
            import uvloop
            uvloop.install()
            import uvicorn
            uvicorn.run(ServerAPP.app, host="0.0.0.0",
                        port=5031,
                        loop="uvloop",
                        log_level="warning")
