import tornado.web

from waterbutler.identity import get_identity
from waterbutler.providers import core
from waterbutler.utils import lazyproperty


def list_or_value(value):
    assert isinstance(value, list)
    if len(value) == 0:
        return None
    if len(value) == 1:
        return value[0].decode('utf-8')
    return [item.decode('utf-8') for item in value]


class ConvienceHandler(tornado.web.RequestHandler):
    @lazyproperty
    def arguments(self):
        args = {
            key: list_or_value(value)
            for key, value in self.request.query_arguments.items()
        }
        args['action'] = self.ACTION_MAP[self.request.method]
        return args

    @lazyproperty
    def credentials(self):
        return (yield from fetch_identity(self.arguments))

    @lazyproperty
    def provider(self):
        return core.make_provider(
            self.arguments['provider'],
            self.credentials
        )

    def prepare(self):
        self.provider
