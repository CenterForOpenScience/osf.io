import asyncio

import tornado.web
import tornado.platform.asyncio
from raven.contrib.tornado import AsyncSentryClient

from waterbutler import settings
from waterbutler.server.handlers import crud
from waterbutler.server.handlers import metadata
from waterbutler.server.handlers import revisions
from waterbutler.server import settings as server_settings


def make_app(debug):

    app = tornado.web.Application(
        [
            (r'/file', crud.CRUDHandler),
            (r'/data', metadata.MetadataHandler),
            (r'/revisions', revisions.RevisionHandler),
        ],
        debug=debug,
    )
    app.sentry_client = AsyncSentryClient(settings.get('SENTRY_DSN', None))
    return app


def serve():
    tornado.platform.asyncio.AsyncIOMainLoop().install()

    app = make_app(server_settings.DEBUG)
    app.listen(server_settings.PORT, server_settings.ADDRESS)

    asyncio.get_event_loop().set_debug(server_settings.DEBUG)
    asyncio.get_event_loop().run_forever()
