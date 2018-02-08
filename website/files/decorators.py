import httplib
import functools
from osf.models import BaseFileNode, Guid
from framework.exceptions import HTTPError

def _kwargs_to_file(kwargs):
    """Retrieve file object from keyword arguments.

    :param dict kwargs: Dictionary of keyword arguments
    :return: File object

    """
    id_or_guid = kwargs.get('fid_or_guid')
    file = BaseFileNode.active.filter(_id=id_or_guid).first()
    if not file:
        guid = Guid.load(id_or_guid)
        if guid:
            file = guid.referent
        else:
            raise HTTPError(httplib.NOT_FOUND, data={
                'message_short': 'File Not Found',
                'message_long': 'The requested file could not be found.'
            })
    if not file.is_file:
        raise HTTPError(httplib.BAD_REQUEST, data={
            'message_long': 'Downloading folders is not permitted.'
        })

    return file


def _inject_file_and_project(kwargs):
    file = _kwargs_to_file(kwargs)
    kwargs['file'] = file
    kwargs['pid'] = file.node._id


def must_be_valid_file(func=None):
    """ Injects file and project. """

    # TODO: Check private link
    def must_be_valid_file_inner(func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):

            _inject_file_and_project(kwargs)

            return func(*args, **kwargs)

        return wrapped

    if func:
        return must_be_valid_file_inner(func)

    return must_be_valid_file_inner
