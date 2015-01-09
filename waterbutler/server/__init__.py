import asyncio
import hashlib

import tornado.web
import tornado.options
import tornado.platform.asyncio


tornado.options.define('port', default=7777, help='The port to server on')
tornado.options.define('host', default='127.0.0.1', help='Where to server WaterButler')
tornado.options.define('chunk_size', default=65536, help='When to flush stream buffers')
tornado.options.define('config', default=None, help='The location of a config file to load')
tornado.options.define('debug', default=True, help='Whether to run tornado in debug mode or not')
tornado.options.define('run_tasks', default=False, help='Whether to run parity and archive tasks')

tornado.options.define('hmac_algorithm', default=hashlib.sha256, callback=lambda x: getattr(hashlib, x), help='The algorithm to sign requests with')
tornado.options.define('hmac_secret', default=b'changeme', type=str, callback=lambda x: x.encode('utf-8'), help='The secret used to sign requests to the identity server')

tornado.options.define('identity_method', default='rest', help='The method used for accessing the identity server')
tornado.options.define('identity_api_url', default='http://127.0.0.1:5000/api/v1/files/auth/', help='The location of the identity server')


def make_app(debug):
    from waterbutler.server.handlers import crud
    from waterbutler.server.handlers import metadata
    from waterbutler.server.handlers import revisions

    return tornado.web.Application(
        [
            (r'/file', crud.CRUDHandler),
            (r'/data', metadata.MetadataHandler),
            (r'/revisions', revisions.RevisionHandler),
        ],
        debug=debug,
    )


def serve():
    tornado.platform.asyncio.AsyncIOMainLoop().install()

    tornado.options.parse_command_line()

    if tornado.options.options.config:
        tornado.options.parse_config_file(tornado.options.options.config)

    app = make_app(tornado.options.options.debug)
    app.listen(tornado.options.options.port, tornado.options.options.host)

    asyncio.get_event_loop().set_debug(tornado.options.options.debug)
    asyncio.get_event_loop().run_forever()
