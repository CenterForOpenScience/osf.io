# encoding: utf-8

import asyncio
import tornado.options
import tornado.platform.asyncio
import tornado.web

from server.handlers import download


def make_app(debug):
    app = tornado.web.Application(
        [
            (r'/files/download', download.DownloadHandler),
        ],
        debug=debug,
    )
    return app


def main(port, address, debug):
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    tornado.options.parse_command_line()

    app = make_app(debug)
    app.listen(port, address)

    asyncio.get_event_loop().set_debug(debug)
    asyncio.get_event_loop().run_forever()
