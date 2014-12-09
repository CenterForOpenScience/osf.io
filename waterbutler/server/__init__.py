# encoding: utf-8

import asyncio
import tornado.options
import tornado.platform.asyncio
import tornado.web

from waterbutler.server.handlers import download
from waterbutler.server.handlers import upload


def make_app(debug):
    app = tornado.web.Application(
        [
            (r'/file', upload.CRUDHandler),
            # (r'/file/download', download.DownloadHandler),
            # (r'/file/upload', upload.UploadHandler),
        ],
        debug=debug,
    )
    return app


def serve(port, address, debug):
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    tornado.options.parse_command_line()

    app = make_app(debug)
    app.listen(port, address)

    asyncio.get_event_loop().set_debug(debug)
    asyncio.get_event_loop().run_forever()
