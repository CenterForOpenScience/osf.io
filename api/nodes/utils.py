# -*- coding: utf-8 -*-
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.status import is_server_error
import requests

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from website.util import waterbutler_api_url_for

from api.base.exceptions import ServiceUnavailableError
from api.base.utils import get_object_or_error

def get_file_object(node, path, provider, request):
    # Don't bother going to waterbutler for osfstorage
    if provider == 'osfstorage':
        # Kinda like /me for a user
        # The one odd case where path is not really path
        if path == '/':
            obj = node.get_addon('osfstorage').get_root()
        else:
            if path.endswith('/'):
                model = OsfStorageFolder
            else:
                model = OsfStorageFile
            obj = get_object_or_error(model, Q(node=node.pk, _id=path.strip('/')), request)
        return obj

    if not node.get_addon(provider) or not node.get_addon(provider).configured:
        raise NotFound('The {} provider is not configured for this project.'.format(provider))

    view_only = request.query_params.get('view_only', default=None)
    url = waterbutler_api_url_for(node._id, provider, path, _internal=True,
                                  meta=True, view_only=view_only)

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
