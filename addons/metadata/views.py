# -*- coding: utf-8 -*-
import json
from rest_framework import status as http_status
from flask import request
from flask import make_response
import logging

from . import SHORT_NAME
from . import settings
from .models import ERadRecord, RegistrationReportFormat
from .utils import make_report_as_csv
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from osf.models import DraftRegistration
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
FIELD_GRDM_FILES = 'grdm-files'


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

def _schema_has_field(schema, name):
    questions = sum([page['questions'] for page in schema['pages']], [])
    qids = [q['qid'] for q in questions]
    return name in qids

def _get_file_metadata_for_schema(schema_id, file_metadata):
    assert not file_metadata['generated']
    items = [item for item in file_metadata['items'] if item['schema'] == schema_id]
    if len(items) == 0:
        return None
    if not items[0]['active']:
        return None
    return {
        'path': file_metadata['path'],
        'folder': file_metadata['folder'],
        'metadata': items[0]['data'],
    }

def _get_draft_files(draft_metadata):
    if FIELD_GRDM_FILES not in draft_metadata:
        return []
    draft_files = draft_metadata[FIELD_GRDM_FILES]
    if 'value' not in draft_files:
        return []
    draft_value = draft_files['value']
    if draft_value == '':
        return []
    return json.loads(draft_value)


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
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_file_to_drafts(auth, did=None, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        draft_schema = draft.registration_schema.schema
        if not _schema_has_field(draft_schema, FIELD_GRDM_FILES):
            logger.error('No grdm-files metadata: schema={}'.format(
                draft.registration_schema._id,
            ))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        draft_files = _get_draft_files(draft_metadata)
        file_metadata_ = addon.get_file_metadata_for_path(filepath)
        file_metadata = _get_file_metadata_for_schema(
            draft.registration_schema._id,
            file_metadata_
        )
        if file_metadata is None:
            logger.error('No file metadata: schema={}, filepath={}'.format(
                draft.registration_schema._id,
                filepath,
            ))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        logger.info('Draft: draft={}, file_metadata={}'.format(draft_files, file_metadata))
        draft_files = [df
                       for df in draft_files
                       if df['path'] != file_metadata['path']]
        draft_files.append(file_metadata)
        draft.update_metadata({
            FIELD_GRDM_FILES: {
                'value': json.dumps(draft_files, indent=2),
            },
        })
        draft.save()
        return _response_file_metadata(addon, filepath)
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_delete_file_from_drafts(auth, did=None, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        draft_schema = draft.registration_schema.schema
        if not _schema_has_field(draft_schema, FIELD_GRDM_FILES):
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        draft_files = _get_draft_files(draft_metadata)
        logger.info('Draft: draft={}'.format(draft_files))
        draft_files = [df
                       for df in draft_files
                       if df['path'] != filepath]
        draft.update_metadata({
            FIELD_GRDM_FILES: {
                'value': json.dumps(draft_files, indent=2),
            },
        })
        draft.save()
        return _response_file_metadata(addon, filepath)
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def metadata_report_list_view(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_export_csv(auth, did=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        formats = RegistrationReportFormat.objects.filter(registration_schema=draft.registration_schema)
        formats = [f for f in formats if f.csv_template]
        if len(formats) == 0:
            logger.error('No report format for {}'.format(draft.registration_schema.name))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        filename, csvcontent = make_report_as_csv(formats[0], draft_metadata)
        response = make_response()
        response.data = csvcontent.encode('utf8')
        response.mimetype = 'text/csv;charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)
