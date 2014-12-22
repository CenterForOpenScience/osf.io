import asyncio

import tornado.options
import tornado.platform.asyncio
import tornado.web

from waterbutler.server.handlers import crud
from waterbutler.server.handlers import metadata
from waterbutler.server.handlers import revisions


def make_app(debug):
    app = tornado.web.Application(
        [
            (r'/file', crud.CRUDHandler),
            (r'/data', metadata.MetadataHandler),
            (r'/revisions', revisions.RevisionHandler),
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
