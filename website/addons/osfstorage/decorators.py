import httplib
import functools

from modularodm.exceptions import NoResultsFound
from modularodm.storage.base import KeyExistsException
from framework.auth.decorators import must_be_signed

from framework.exceptions import HTTPError

from website.models import User
from website.models import Node
from website.files import models
from website.files import exceptions
from website.project.decorators import (
    must_not_be_registration, must_have_addon,
)


def handle_odm_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoResultsFound:
            raise HTTPError(httplib.NOT_FOUND)
        except KeyExistsException:
            raise HTTPError(httplib.CONFLICT)
        except exceptions.VersionNotFoundError:
            raise HTTPError(httplib.NOT_FOUND)
    return wrapped


def autoload_filenode(must_be=None, default_root=False):
    """Implies both must_have_addon osfstorage node and
    handle_odm_errors
    Attempts to load fid as a OsfStorageFileNode with viable constraints
    """
    def _autoload_filenode(func):
        @handle_odm_errors
        @must_have_addon('osfstorage', 'node')
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            node = kwargs['node']

            if 'fid' not in kwargs and default_root:
                file_node = kwargs['node_addon'].get_root()
            else:
                file_node = models.OsfStorageFileNode.get(kwargs.get('fid'), node)

            if must_be and file_node.kind != must_be:
                raise HTTPError(httplib.BAD_REQUEST, data={
                    'message_short': 'incorrect type',
                    'message_long': 'FileNode must be of type {} not {}'.format(must_be, file_node.kind)
                })

            kwargs['file_node'] = file_node

            return func(*args, **kwargs)

        return wrapped
    return _autoload_filenode


def waterbutler_opt_hook(func):

    @must_be_signed
    @handle_odm_errors
    @must_not_be_registration
    @must_have_addon('osfstorage', 'node')
    @functools.wraps(func)
    def wrapped(payload, *args, **kwargs):
        try:
            user = User.load(payload['user'])
            dest_node = Node.load(payload['destination']['node'])
            source = models.OsfStorageFileNode.get(payload['source'], kwargs['node'])
            dest_parent = models.OsfStorageFolder.get(payload['destination']['parent'], dest_node)

            kwargs.update({
                'user': user,
                'source': source,
                'destination': dest_parent,
                'name': payload['destination']['name'],
            })
        except KeyError:
            raise HTTPError(httplib.BAD_REQUEST)

        return func(*args, **kwargs)
    return wrapped
