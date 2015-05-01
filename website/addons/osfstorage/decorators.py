import httplib
import functools

from webargs import Arg
from webargs import core

from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError
from modularodm.storage.base import KeyExistsException
from framework.auth.decorators import must_be_signed

from website.models import User
from website.models import Node
from website.addons.osfstorage import model
from framework.exceptions import HTTPError
from website.addons.osfstorage import utils
from website.project.decorators import (
    must_not_be_registration, must_have_addon,
)


USER_ARG = Arg(None, required=True, dest='user', use=User.from_cookie, validate=lambda x: x is not None)

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

    def error_callback(self, err):
        raise HTTPError(err.status_code, data={
            'message_long': err.message
        })

def path_validator(path):
    return (
        path.startswith('/') and
        len(path.strip('/').split('/')) < 3
    )

file_opt_args = {
    'user': Arg(None, required=True, use=User.load, validate=lambda x: x is not None),
    'source': Arg(unicode, required=True),
    'destination': Arg({
        'name': Arg(unicode, required=True, validate=lambda x: '/' not in x),
        'parent': Arg(unicode, required=True, validate=lambda x: '/' not in x),
        'node': Arg(None, required=True, dest='node', use=Node.load, validate=lambda x: x is not None),
    })
}

waterbutler_crud_args = {
    'cookie': USER_ARG,
    'path': Arg(str, required=True, validate=path_validator),
}


def handle_odm_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoResultsFound:
            raise HTTPError(httplib.NOT_FOUND)
        except KeyExistsException:
            raise HTTPError(httplib.CONFLICT)
    return wrapped


def waterbutler_opt_hook(func):

    @must_be_signed
    @handle_odm_errors
    @must_not_be_registration
    @must_have_addon('osfstorage', 'node')
    @functools.wraps(func)
    def wrapped(payload, *args, **kwargs):
        kwargs.update(JSONParser(payload).parse(file_opt_args))
        destination = kwargs['destination']
        kwargs.update({
            'source': model.OsfStorageFileNode.get(
                kwargs['source'],
                kwargs['node_addon']
            ),
            'destination': model.OsfStorageFileNode.get_folder(
                destination['parent'],
                destination['node'].get_addon('osfstorage')
            ),
            'name': destination['name'],
        })
        return func(*args, **kwargs)
    wrapped.undecorated = func  # For testing
    return wrapped


@must_be_signed
@handle_odm_errors
@must_not_be_registration
@must_have_addon('osfstorage', 'node')
def waterbutler_crud_hook(func):

    @functools.wraps(func)
    def wrapped(payload, *args, **kwargs):
        kwargs.update(JSONParser(payload)).parse({
            'cookie': USER_ARG,
            'path': Arg(
                None,
                required=True,
                dest='file_node',
                validate=lambda x: model.OsfStorageFileNode.get(x, kwargs.get('node_addon'))
            ),
        })

        return func(*args, **kwargs)
    return wrapped
