import asyncio

import tornado.web
import tornado.httpserver
import tornado.platform.asyncio

from waterbutler import settings
from waterbutler.core.utils import AioSentryClient
from waterbutler.server.handlers import crud
from waterbutler.server.handlers import status
from waterbutler.server.handlers import metadata
from waterbutler.server.handlers import revisions
from waterbutler.server.handlers import zip
from waterbutler.server import settings as server_settings


def make_app(debug):
    app = tornado.web.Application(
        [
            (r'/file', crud.CRUDHandler),
            (r'/data', metadata.MetadataHandler),
            (r'/status', status.StatusHandler),
            (r'/revisions', revisions.RevisionHandler),
            (r'/zip', zip.ZipHandler),
        ],
        debug=debug,
    )
    app.sentry_client = AioSentryClient(settings.get('SENTRY_DSN', None))
    return app


def serve():
    tornado.platform.asyncio.AsyncIOMainLoop().install()

    app = make_app(server_settings.DEBUG)

    ssl_options = None
    if server_settings.SSL_CERT_FILE and server_settings.SSL_KEY_FILE:
        ssl_options = {
            'certfile': server_settings.SSL_CERT_FILE,
            'keyfile': server_settings.SSL_KEY_FILE,
        }

    app.listen(
        server_settings.PORT,
        address=server_settings.ADDRESS,
        xheaders=server_settings.XHEADERS,
        max_buffer_size=server_settings.MAX_BUFFER_SIZE,
        ssl_options=ssl_options,
    )

    asyncio.get_event_loop().set_debug(server_settings.DEBUG)
    asyncio.get_event_loop().run_forever()
