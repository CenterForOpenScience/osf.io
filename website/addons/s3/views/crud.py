# -*- coding: utf-8 -*-

import urllib
import datetime
import httplib as http

from boto.exception import S3ResponseError, BotoClientError

from flask import request

from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect

from website.models import NodeLog

from website.project.decorators import (
    must_have_permission, must_be_contributor_or_public,
    must_not_be_registration, must_have_addon
)

from website.addons.s3.api import S3Wrapper, create_bucket

from website.addons.s3.utils import (
    build_urls, generate_signed_url,
    validate_bucket_name
)


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_download(**kwargs):

    node_settings = kwargs['node_addon']
    key_name = urllib.unquote(kwargs['path'])
    vid = request.args.get('vid')

    if key_name is None:
        raise HTTPError(http.NOT_FOUND)
    connect = S3Wrapper.from_addon(node_settings)
    if not connect.does_key_exist(key_name):
        raise HTTPError(http.NOT_FOUND)
    return redirect(connect.download_file_URL(key_name, vid))


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('s3', 'node')
def s3_delete(**kwargs):

    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']
    dfile = urllib.unquote(kwargs['path'])

    connect = S3Wrapper.from_addon(node_settings)
    connect.delete_file(dfile)

    node.add_log(
        action='s3_' + NodeLog.FILE_REMOVED,
        params={
            'project': node.parent_id,
            'node': node._id,
            'bucket': node_settings.bucket,
            'path': dfile,
        },
        auth=kwargs['auth'],
        log_date=datetime.datetime.utcnow(),
    )
    return {}


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('s3', 'node')
def s3_upload(**kwargs):

    node = kwargs['node'] or kwargs['project']
    s3 = kwargs['node_addon']

    file_name = request.json.get('name')
    if file_name is None:
        raise HTTPError(http.BAD_REQUEST)
    file_name = urllib.quote_plus(file_name.encode('utf-8'))
    mime = request.json.get('type') or 'application/octet-stream'

    update = S3Wrapper.from_addon(s3).does_key_exist(file_name)
    signed_url = generate_signed_url(mime, file_name, s3)
    node.add_log(
        action='s3_' +
        (NodeLog.FILE_UPDATED if update else NodeLog.FILE_ADDED),
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'bucket': s3.bucket,
            'path': file_name,
            'urls': build_urls(node, file_name),
        },
        auth=kwargs['auth'],
        log_date=datetime.datetime.utcnow(),
    )
    return signed_url


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def create_new_bucket(**kwargs):
    user = kwargs['auth'].user
    user_settings = user.get_addon('s3')
    bucket_name = request.json.get('bucket_name')

    if not validate_bucket_name(bucket_name):
        return {'message': 'That bucket name is not valid.'}, http.NOT_ACCEPTABLE
    try:
        create_bucket(user_settings, request.json.get('bucket_name'))
        return {}
    except BotoClientError as e:
        return {'message': e.message}, http.NOT_ACCEPTABLE
    except S3ResponseError as e:
        return {'message': e.message}, http.NOT_ACCEPTABLE


@must_be_contributor_or_public  # returns user, project
@must_have_addon('s3', 'node')
def file_delete_info(**kwargs):
    node = kwargs['node'] or kwargs['project']
    api_url = node.api_url
    files_page_url = node.web_url_for('collect_file_trees')
    if files_page_url is None or api_url is None:
        raise HTTPError(http.NOT_FOUND)
    return {
        'api_url': api_url,
        'files_page_url': files_page_url,
    }
