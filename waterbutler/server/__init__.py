import asyncio

import tornado.web
import tornado.platform.asyncio
from raven.contrib.tornado import AsyncSentryClient


def make_app(debug):
    from waterbutler import settings
    from waterbutler.server.handlers import crud
    from waterbutler.server.handlers import metadata
    from waterbutler.server.handlers import revisions

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
    from waterbutler.server import settings

    tornado.platform.asyncio.AsyncIOMainLoop().install()

    app = make_app(settings.DEBUG)
    app.listen(settings.PORT, settings.ADDRESS)

    asyncio.get_event_loop().set_debug(settings.DEBUG)
    asyncio.get_event_loop().run_forever()
