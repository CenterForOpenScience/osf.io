# -*- coding: utf-8 -*-
from modularodm import Q
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.status import is_server_error
import requests

from website.files.models import OsfStorageFileNode
from website.util import waterbutler_api_url_for

from api.base.exceptions import ServiceUnavailableError
from api.base.utils import get_object_or_error

def get_file_object(node, path, provider, request):
    if provider == 'osfstorage':
        # Kinda like /me for a user
        # The one odd case where path is not really path
        if path == '/':
            obj = node.get_addon('osfstorage').get_root()
        else:
            obj = get_object_or_error(
                OsfStorageFileNode,
                Q('node', 'eq', node._id) &
                Q('_id', 'eq', path.strip('/')) &
                Q('is_file', 'eq', not path.endswith('/'))
            )
        return obj

    if not node.has_addon(provider):
        raise NotFound('The {} provider is not configured for this project.'.format(provider))

    url = waterbutler_api_url_for(node._id, provider, path, meta=True)
    waterbutler_request = requests.get(
        url,
        cookies=request.COOKIES,
        headers={'Authorization': request.META.get('HTTP_AUTHORIZATION')},
    )

    if waterbutler_request.status_code == 401:
        raise PermissionDenied

    if waterbutler_request.status_code == 404:
        raise NotFound

    if is_server_error(waterbutler_request.status_code):
        raise ServiceUnavailableError(detail='Could not retrieve files information at this time.')

    try:
        return waterbutler_request.json()['data']
    except KeyError:
        raise ServiceUnavailableError(detail='Could not retrieve files information at this time.')
