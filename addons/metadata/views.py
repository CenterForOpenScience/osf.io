# -*- coding: utf-8 -*-
import codecs
import json
from rest_framework import status as http_status
from flask import request
from flask import make_response
import logging

from . import SHORT_NAME
from .models import RegistrationReportFormat, get_draft_files, FIELD_GRDM_FILES, schema_has_field
from .utils import make_report_as_csv
from .suggestion import suggestion_metadata, _erad_candidates, valid_suggestion_key
from .packages import import_project, export_project, get_task_result
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in
from framework.flask import redirect
from osf.models import AbstractNode, DraftRegistration, Registration
from osf.models.metaschema import RegistrationSchema
from osf.utils.permissions import WRITE
from website.project.decorators import (
    must_be_valid_project,
    must_have_addon,
    must_have_permission,
    must_be_contributor,
)
from website.ember_osf_web.views import use_ember_app
from website.util import web_url_for, api_url_for


logger = logging.getLogger(__name__)


def _response_config(addon):
    return {
        'data': {
            'type': 'metadata-config',
            'attributes': {
                'imported_addon_settings': [{
                    'name': imported.name,
                    'folder_id': imported.folder_id,
                    'applicable': imported.is_applicable,
                    'applied': imported.is_applied,
                    'full_name': imported.full_name,
                } for imported in addon.imported_addon_settings.all()],
            }
        }
    }

def _response_project_metadata(user, addon):
    attr = {
        'editable': addon.owner.has_permission(user, WRITE),
    }
    attr.update(addon.get_project_metadata())
    return {
        'data': {
            'id': addon.owner._id,
            'type': 'metadata-node-project',
            'attributes': attr,
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

def _response_schemas(addon, schemas):
    return {
        'data': {
            'id': addon.owner._id,
            'type': 'metadata-node-schema',
            'attributes': addon.get_report_formats_for(schemas),
        }
    }

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
        'urlpath': file_metadata['urlpath'],
        'metadata': items[0]['data'],
    }

def _get_file_metadata_node(node, metadata_node_id):
    if node._id == metadata_node_id:
        return node
    nodes = [n for n in node.nodes if n._id == metadata_node_id]
    if len(nodes) == 0:
        raise ValueError('Unexpected node ID: {}'.format(metadata_node_id))
    return AbstractNode.objects.filter(guids___id=metadata_node_id).first()

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_config(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return _response_config(addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def metadata_update_config(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    addon_names = request.json.get('addons', [])
    if len(addon_names) == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    try:
        addon.apply_imported_addon_settings(addon_names, auth)
    except ValueError:
        logger.exception('Failed to apply imported addon settings')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return _response_config(addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
def metadata_get_erad_candidates(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    candidates = []
    for user in node.contributors:
        rn = user.erad
        if rn is None:
            continue
        candidates += _erad_candidates(kenkyusha_no=rn)
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
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_project(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return _response_project_metadata(auth.user, addon)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_schemas(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    schemas = [schema
               for schema in RegistrationSchema.objects.all()
               if schema_has_field(schema.schema, FIELD_GRDM_FILES)]
    return _response_schemas(addon, schemas)

@must_be_valid_project
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_get_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        addon.set_file_metadata(filepath, request.json, auth=auth)
    except ValueError:
        logger.exception('Invalid metadata')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_file_hash(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        addon.set_file_hash(filepath, request.json['hash'])
    except KeyError as e:
        logger.error('Invalid hash: ' + str(e))
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_delete_file(auth, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    addon.delete_file_metadata(filepath, auth=auth)
    return _response_file_metadata(addon, filepath)

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_set_file_to_drafts(auth, did=None, mnode=None, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    mnode_obj = _get_file_metadata_node(node, mnode)
    addon = mnode_obj.get_addon(SHORT_NAME)
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        draft_schema = draft.registration_schema.schema
        if not schema_has_field(draft_schema, FIELD_GRDM_FILES):
            logger.error('No grdm-files metadata: schema={}'.format(
                draft.registration_schema._id,
            ))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        draft_files = get_draft_files(draft_metadata)
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
        if node._id != mnode_obj._id:
            file_metadata['path'] = '{}/{}'.format(mnode_obj._id, file_metadata['path'])
        draft_files = [df
                       for df in draft_files
                       if df['path'] != file_metadata['path']]
        draft_files.append(file_metadata)
        draft.update_metadata({
            FIELD_GRDM_FILES: {
                'value': json.dumps(draft_files, indent=2) if len(draft_files) > 0 else '',
            },
        })
        draft.save()
        return _response_file_metadata(addon, filepath)
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_delete_file_from_drafts(auth, did=None, mnode=None, filepath=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    mnode_obj = _get_file_metadata_node(node, mnode)
    addon = mnode_obj.get_addon(SHORT_NAME)
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        draft_schema = draft.registration_schema.schema
        if not schema_has_field(draft_schema, FIELD_GRDM_FILES):
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        draft_files = get_draft_files(draft_metadata)
        logger.info('Draft: draft={}'.format(draft_files))
        draft_filepath = filepath
        if node._id != mnode_obj._id:
            draft_filepath = '{}/{}'.format(mnode_obj._id, filepath)
        draft_files = [df
                       for df in draft_files
                       if df['path'] != draft_filepath]
        draft.update_metadata({
            FIELD_GRDM_FILES: {
                'value': json.dumps(draft_files, indent=2) if len(draft_files) > 0 else '',
            },
        })
        draft.save()
        return _response_file_metadata(addon, filepath)
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_be_contributor
@must_have_addon(SHORT_NAME, 'node')
def metadata_report_list_view(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_be_contributor
@must_have_addon(SHORT_NAME, 'node')
def metadata_package_view(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_export_draft_registrations_csv(auth, did=None, **kwargs):
    node = kwargs['node'] or kwargs['project']
    try:
        draft = DraftRegistration.objects.get(_id=did, branched_from=node)
        formats = RegistrationReportFormat.objects.filter(registration_schema_id=draft.registration_schema._id)
        formats = [f for f in formats if f.csv_template]
        name = request.args.get('name', None)
        if name is not None:
            formats = [f for f in formats if f.name == name]
        if len(formats) == 0:
            logger.error('No report format for {} (name={})'
                .format(draft.registration_schema.name, name))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        draft_metadata = draft.registration_metadata
        schema = draft.registration_schema.schema
        filename, csvcontent = make_report_as_csv(formats[0], draft_metadata, schema)
        response = make_response()
        response.data = codecs.BOM_UTF16_LE + csvcontent.encode('utf-16-le')
        response.mimetype = 'text/csv;charset=utf-16'
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response
    except DraftRegistration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_have_permission('read')
def metadata_export_registrations_csv(auth, rid=None, **kwargs):
    registration = kwargs['node'] or kwargs['project']
    try:
        formats = RegistrationReportFormat.objects.filter(registration_schema_id=registration.registration_schema._id)
        formats = [f for f in formats if f.csv_template]
        name = request.args.get('name', None)
        if name is not None:
            formats = [f for f in formats if f.name == name]
        if len(formats) == 0:
            logger.error('No report format for {} (name={})'
                .format(registration.registration_schema.name, name))
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
        registration_metadata = registration.get_registration_metadata(
            registration.registration_schema
        )
        schema = registration.registration_schema.schema
        filename, csvcontent = make_report_as_csv(formats[0], registration_metadata, schema)
        response = make_response()
        response.data = codecs.BOM_UTF16_LE + csvcontent.encode('utf-16-le')
        response.mimetype = 'text/csv;charset=utf-16'
        response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response
    except Registration.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('write')
@must_have_addon(SHORT_NAME, 'node')
def metadata_file_metadata_suggestions(auth, filepath=None, **kwargs):
    key_list = request.args.getlist('key[]', None) or request.args.get('key', None)
    if key_list is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    if type(key_list) is str:
        key_list = [key_list]
    if any([not valid_suggestion_key(key) for key in key_list]):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    keyword = request.args.get('keyword', '').lower()
    node = kwargs['node'] or kwargs['project']
    suggestions = sum([  # flatten
        suggestion_metadata(key, keyword, filepath, node)
        for key in key_list
    ], [])
    return {
        'data': {
            'id': node._id,
            'type': 'file-metadata-suggestion',
            'attributes': {
                'filepath': filepath,
                'suggestions': suggestions
            }
        }
    }

@must_be_logged_in
def metadata_import_project_page(auth):
    title = request.args.get('title', '')
    url = request.args.get('url', None)
    if url is None:
        logger.warning('Missing parameters: url')
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    return {
        'url': url,
        'default_title': title,
    }

@must_be_logged_in
def metadata_import_project(auth):
    task = import_project.delay(
        request.json['url'],
        auth.user._id,
        request.json['title'],
    )
    return {
        'task_id': task.task_id,
        'progress_url': web_url_for('metadata_task_progress_page', taskid=task.task_id),
    }

@must_be_logged_in
def metadata_task_progress_page(auth, taskid=None, **kwargs):
    result = get_task_result(auth, taskid)
    if result['state'] == 'SUCCESS':
        return redirect(result['info']['node_url'])
    return {
        'task_id': taskid,
        'result': result,
    }

@must_be_logged_in
def metadata_task_progress(auth, taskid=None):
    return get_task_result(auth, taskid)

@must_be_valid_project
@must_be_logged_in
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_export_project(auth, **kwargs):
    node = kwargs['node'] or kwargs['project']
    task = export_project.delay(
        auth.user._id,
        node._id,
        request.json,
    )
    return {
        'node_id': node._id,
        'task_id': task.task_id,
        'progress_api_url': api_url_for(
            'metadata_node_task_progress',
            **dict([(k, v) for k, v in kwargs.items() if k in ['nid', 'pid']] + [('taskid', task.task_id)]),
        ),
    }

@must_be_valid_project
@must_have_permission('read')
@must_have_addon(SHORT_NAME, 'node')
def metadata_node_task_progress(auth, taskid=None, **kwargs):
    return get_task_result(auth, taskid)
