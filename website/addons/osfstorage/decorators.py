import functools

from webargs import Arg
from webargs import core

from framework.auth.decorators import must_be_signed

from website.models import User
from framework.exceptions import HTTPError
from website.addons.osfstorage import utils
from website.project.decorators import (
    must_not_be_registration, must_have_addon,
)


class JSONParser(core.Parser):
    def __init__(self, data):
        self._data = data

    def parse(self, args):
        return super(JSONParser, self).parse(args, None, ('json',))

    def parse_json(self, _, name, arg):
        if self._data:
            return core.get_value(self._data, name, arg.multiple)
        else:
            return core.Missing

def path_validator(path):
    return (
        path.startswith('/') and
        len(path.strip('/').split('/')) < 3
    )

file_opt_args = {
    'source': Arg({
        'path': Arg(str, required=True, validate=path_validator),
        'cookie': Arg(None, required=True, use=User.from_cookie, validate=lambda x: x is not None)
    }),
    'destination': Arg({
        'path': Arg(str, required=True, validate=path_validator),
        'cookie': Arg(None, required=True, use=User.from_cookie, validate=lambda x: x is not None)
    })
}


def waterbutler_opt_hook(func):

    @must_be_signed
    @utils.handle_odm_errors
    @must_not_be_registration
    @must_have_addon('osfstorage', 'node')
    @functools.wraps(func)
    def wrapped(payload, *args, **kwargs):
        kwargs.update(JSONParser(payload).parse(file_opt_args))
        return func(*args, **kwargs)
    return wrapped

