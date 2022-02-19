# -*- coding: utf-8 -*-
from rest_framework import status as http_status
from flask import request
import logging

from . import SHORT_NAME
from . import settings
from .models import ERadRecord
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from admin.rdm_addons.decorators import must_be_rdm_addons_allowed
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon,
    must_have_permission,
)
from website.ember_osf_web.views import use_ember_app


logger = logging.getLogger(__name__)

ERAD_COLUMNS = [
    'KENKYUSHA_NO', 'KENKYUSHA_SHIMEI', 'KENKYUKIKAN_CD', 'KENKYUKIKAN_MEI',
    'HAIBUNKIKAN_CD', 'HAIBUNKIKAN_MEI', 'NENDO', 'SEIDO_CD', 'SEIDO_MEI',
    'JIGYO_CD', 'JIGYO_MEI', 'KADAI_ID', 'KADAI_MEI', 'BUNYA_CD', 'BUNYA_MEI'
]


def _response_user_erad_config(addon):
    return {
        'data': {
            'id': addon.owner._id,
            'type': 'metadata-user-erad',
            'attributes': {
                'researcher_number': addon.get_erad_researcher_number() if addon else None,
            }
        }
    }

def _response_project_metadata(addon):
    return {
        'data': {
            'id': addon.owner._id,
            'type': 'metadata-node-project',
            'attributes': addon.get_project_metadata(),
        }
    }

def _response_file_metadata(addon, path):
    return {
        'data': {
            'id': addon.owner._id,
            'type': 'metadata-node-file',
            'attributes': addon.get_file_metadata_for_path(path),
        }
    }

def _erad_candidates(researcher_number):
    r = []
    for record in ERadRecord.objects.filter(kenkyusha_no=researcher_number):
        r.append(dict([(k.lower(), getattr(record, k.lower()))
                       for k in ERAD_COLUMNS]))
    return r

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def metadata_get_user_erad_config(auth, **kwargs):
    addon = auth.user.get_addon(SHORT_NAME)
    return _response_user_erad_config(addon)

@must_be_logged_in
@must_be_rdm_addons_allowed(SHORT_NAME)
def metadata_set_user_erad_config(auth, **kwargs):
    addon = auth.user.get_addon(SHORT_NAME)
    if not addon:
        auth.user.add_addon(SHORT_NAME)
        addon = auth.user.get_addon(SHORT_NAME)
    try:
        researcher_number = request.json['researcher_number']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    addon.set_erad_researcher_number(researcher_number)
    return _response_user_erad_config(addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
def metadata_get_erad_candidates(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    candidates = []
    for user in node.contributors:
        addon = user.get_addon(SHORT_NAME)
        if addon is None:
            continue
        rn = addon.get_erad_researcher_number()
        if rn is None:
            continue
        candidates += _erad_candidates(rn)
    return {
        'data': {
            'id': node._id,
            'type': 'metadata-node-erad',
            'attributes': {
                'records': candidates,
            }
        }
    }

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_project(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return _response_project_metadata(addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_project(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        addon.set_project_metadata(request.json)
    except ValueError as e:
        logger.error('Invalid metadata: ' + str(e))
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return _response_project_metadata(addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        addon.set_file_metadata(filepath, request.json)
    except ValueError as e:
        logger.error('Invalid metadata: ' + str(e))
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_delete_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    addon.delete_file_metadata(filepath)
    return _response_file_metadata(addon, filepath)


@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def metadata_report_list_view(**kwargs):
    return use_ember_app()
