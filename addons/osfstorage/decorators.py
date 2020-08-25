from rest_framework import status as http_status
import functools

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError

from framework.auth.decorators import must_be_signed

from framework.exceptions import HTTPError

from addons.osfstorage.models import OsfStorageFileNode, OsfStorageFolder
from osf.models import OSFUser, Guid
from website.files import exceptions
from website.project.decorators import (
    must_not_be_registration,
)

def handle_django_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            raise HTTPError(http_status.HTTP_409_CONFLICT)
        except exceptions.VersionNotFoundError:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
    return wrapped


def load_guid_as_target(func):

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        guid = kwargs.get('guid')
        target = getattr(Guid.load(guid), 'referent', None)
        if not target:
            raise HTTPError(
                http_status.HTTP_404_NOT_FOUND,
                data={
                    'message_short': 'Guid not resolved',
                    'message_long': 'No object with that guid could be found',
                }
            )
        kwargs['target'] = target
        return func(*args, **kwargs)

    return wrapped


def autoload_filenode(must_be=None, default_root=False):
    """Implies handle_django_errors
    Attempts to load fid as a OsfStorageFileNode with viable constraints
    """
    def _autoload_filenode(func):
        @handle_django_errors
        @load_guid_as_target
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            if 'fid' not in kwargs and default_root:
                file_node = OsfStorageFolder.objects.get_root(kwargs['target'])
            else:
                file_node = OsfStorageFileNode.get(kwargs.get('fid'), kwargs['target'])
            if must_be and file_node.kind != must_be:
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                    'message_short': 'incorrect type',
                    'message_long': 'FileNode must be of type {} not {}'.format(must_be, file_node.kind)
                })

            kwargs['file_node'] = file_node

            return func(*args, **kwargs)

        return wrapped
    return _autoload_filenode


def waterbutler_opt_hook(func):

    @must_be_signed
    @handle_django_errors
    @must_not_be_registration
    @load_guid_as_target
    @functools.wraps(func)
    def wrapped(payload, *args, **kwargs):
        try:
            user = OSFUser.load(payload['user'])
            # Waterbutler is sending back ['node'] under the destination payload - WB should change to target
            target = payload['destination'].get('target') or payload['destination'].get('node')
            dest_target = Guid.load(target).referent
            source = OsfStorageFileNode.get(payload['source'], kwargs['target'])
            dest_parent = OsfStorageFolder.get(payload['destination']['parent'], dest_target)

            kwargs.update({
                'user': user,
                'source': source,
                'destination': dest_parent,
                'name': payload['destination']['name'],
            })
        except KeyError:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

        return func(*args, **kwargs)
    return wrapped
