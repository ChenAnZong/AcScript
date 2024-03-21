from quart import Quart

from export.blue_project import project as blueprint_project
from export.blue_task import task as blueprint_task
import logging
import asyncio


class Config:
    IS_DEBUG = True


class ServerAPP:
    cfg = Config()
    app = Quart(__name__, static_folder='dist')
    app.register_blueprint(blueprint=blueprint_project)
    app.register_blueprint(blueprint=blueprint_task)

    @classmethod
    def start(cls):
        if cls.cfg.IS_DEBUG:
            loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
            print("启动程序#日志打印：", loggers)
            cls.app.run(host="0.0.0.0", port=5031, debug=False)
        else:
            import asyncio
            from hypercorn.config import Config
            from hypercorn.asyncio import serve

            config = Config()
            config._bind = ["0.0.0.0:5031"]
            config.keep_alive_timeout = 0.0
            config.shutdown_timeout = 0.0
            # app.logger.setLevel(logging.DEBUG)
            asyncio.run(serve(cls.app, config))
            # clean()
            # os.system("unset http_proxy")
            # os.system("unset https_proxy")
            # import uvloop
            #
            # uvloop.install()
            # import uvicorn
            #
            # uvicorn.run(app, host="0.0.0.0",
            #             port=5031,
            #             loop="uvloop",
            #             log_level="warning")
