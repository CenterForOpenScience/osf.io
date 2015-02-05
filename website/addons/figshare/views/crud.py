# -*- coding: utf-8 -*-

import os
import datetime
import httplib as http

from urllib2 import urlopen

from flask import request, make_response

from framework.exceptions import HTTPError
from framework.utils import secure_filename

from website.project import decorators  # noqa
from website.project.decorators import must_be_contributor_or_public, must_be_contributor  # noqa
from website.project.decorators import must_have_addon

from ..api import Figshare

# Helpers


# ----------------- PROJECTS ---------------

# PROJECTS: U


@decorators.must_have_permission('write')
@decorators.must_have_addon('figshare', 'node')
@decorators.must_not_be_registration
def figshare_add_article_to_project(**kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')

    project_id = kwargs.get('project_id')
    if project_id is None:
        raise HTTPError(http.BAD_REQUEST)

    article_id = kwargs.get('aid')

    article = None
    connect = Figshare.from_settings(figshare.user_settings)
    if not article_id:
        article = file_as_article(figshare)

    connect.add_article_to_project(figshare, article['article_id'], project_id)

# PROJECTS: D


@decorators.must_have_permission('write')
@decorators.must_have_addon('figshare', 'node')
@decorators.must_not_be_registration
def figshare_remove_article_from_project(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')

    project_id = kwargs.get('project_id') or None
    article_id = kwargs.get('aid') or None

    if project_id is None or article_id is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)
    connect.remove_article_from_project(figshare, article_id, project_id)

# ---------------- ARTICLES -------------------
# ARTICLES: C


def file_as_article(figshare):
    upload = request.files['file']
    filename = secure_filename(upload.filename)
    article = {
        'title': filename,
        'files': [upload]
    }
    return article


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_upload(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')
    upload = request.files['file']
    connect = Figshare.from_settings(figshare.user_settings)
    fs_id = kwargs.get('aid', figshare.figshare_id)

    if fs_id is None:
        raise HTTPError(http.BAD_REQUEST)

    if figshare.figshare_type == 'project' and not kwargs.get('aid', None):
        item = connect.create_article(figshare, file_as_article(upload))
    else:
        item = connect.article(figshare, fs_id)

    if not item:
        raise HTTPError(http.BAD_REQUEST)

    resp = connect.upload_file(node, figshare, item['items'][0], upload)
    #TODO Clean me up
    added = True
    if figshare.figshare_type == 'project' and not kwargs.get('aid', None):
        added = connect.add_article_to_project(figshare, figshare.figshare_id, str(item['items'][0]['article_id']))

    if resp and added:
        node.add_log(
            action='figshare_file_added',
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'path': upload.filename,  # TODO Path?
                'urls': {
                    'view': resp['urls']['view'],
                    'download': resp['urls']['download'],
                },
                'figshare': {
                    'id': figshare.figshare_id,
                    'type': figshare.figshare_type
                }
            },
            auth=kwargs['auth'],
            log_date=datetime.datetime.utcnow(),
        )
        return resp
    else:
        raise HTTPError(http.INTERNAL_SERVER_ERROR)  # TODO better error?


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_upload_file_as_article(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')
    upload = request.files['file']

    project_id = kwargs.get('project_id') or figshare.figshare_id
    if project_id is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)

    article = connect.create_article(figshare, file_as_article(upload))

    rv = connect.upload_file(node, figshare, article['items'][0], upload)
    if rv:
        node.add_log(
            action='figshare_file_added',
            params={
                'project': node.parent_id,
                'node': node._primary_key,
                'path': upload.filename,  # TODO Path?
                'urls': {
                    'view': rv['urls']['view'],
                    'download': rv['urls']['download'],
                },
                'figshare': {
                    'id': figshare.figshare_id,
                    'type': figshare.figshare_type
                }
            },
            auth=kwargs['auth'],
            log_date=datetime.datetime.utcnow(),
        )
        return rv
    else:
        raise HTTPError(http.INTERNAL_SERVER_ERROR)  # TODO better error?


@decorators.must_have_permission('write')
@decorators.must_have_addon('figshare', 'node')
@decorators.must_not_be_registration
def figshare_publish_article(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']

    figshare = node.get_addon('figshare')

    article_id = kwargs.get('aid')

    if article_id is None:
        raise HTTPError(http.BAD_REQUEST)

    cat = request.json.get('category', '')
    tags = request.json.get('tags', '')  # noqa

    if not cat:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)

    connect.update_article(figshare, article_id, {'category_id': cat})

    connect.publish_article(figshare, article_id)
    return {"published": True}

# ARTICLES: D


def figshare_delete_article(*args, **kwargs):
    # TODO implement me?
    pass


# ----------------- FILES --------------------
# FILES: C


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_upload_file_to_article(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']

    figshare = node.get_addon('figshare')

    article = kwargs.get('aid') or None

    connect = Figshare.from_settings(figshare.user_settings)

    if not article:
        article = connect.create_article()

    article = connect.article(figshare, article)['items'][0]

    upload = request.files['file']

    rv = connect.upload_file(
        node,
        figshare,
        article,
        upload
    )

    node.add_log(
        action='figshare_file_added',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'path': upload.filename,  # TODO Path?
            'urls': {
                'view': rv['urls']['view'],
                'download': rv['urls']['download'],
            },
            'figshare': {
                'id': figshare.figshare_id,
                'type': figshare.figshare_type
            }
        },
        auth=kwargs['auth'],
        log_date=datetime.datetime.utcnow(),
    )

    return rv

# FILES: D


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_delete_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']

    figshare = node.get_addon('figshare')

    file_id = kwargs.get('fid', '')
    article_id = kwargs.get('aid', '')

    if file_id is None or article_id is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)
    #connect.remove_article_from_project(figshare, figshare.figshare_id, article_id)
    return connect.delete_file(node, figshare, article_id, file_id)


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_download_file(*args, **kwargs):
    node_settings = kwargs['node_addon']

    article_id = kwargs['aid']
    file_id = kwargs['fid']

    connect = Figshare.from_settings(node_settings.user_settings)

    article = connect.article(node_settings, article_id)
    found = None
    for f in article['items'][0]['files']:
        if str(f['id']) == file_id:
            found = f
    if found:
        f = urlopen(found['download_url'])
        name = found['name']
        filedata = f.read()
        resp = make_response(filedata)
        resp.headers['Content-Disposition'] = 'attachment; filename={0}'.format(name)

        # Add binary MIME type if extension missing
        _, ext = os.path.splitext(name)
        if not ext:
            resp.headers['Content-Type'] = 'application/octet-stream'

        return resp


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_create_project(*args, **kwargs):
    node_settings = kwargs['node_addon']
    project_name = request.json.get('project')
    if not node_settings or not node_settings.has_auth or not project_name:
        raise HTTPError(http.BAD_REQUEST)
    resp = Figshare.from_settings(node_settings.user_settings).create_project(node_settings, project_name)
    if resp:
        return resp
    else:
        raise HTTPError(http.BAD_REQUEST)

@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def figshare_create_fileset(*args, **kwargs):
    node_settings = kwargs['node_addon']
    name = request.json.get('name')
    if not node_settings or not node_settings.has_auth or not name:
        raise HTTPError(http.BAD_REQUEST)
    resp = Figshare.from_settings(node_settings.user_settings).create_article(node_settings, {'title': name}, d_type='fileset')
    if resp:
        return resp
    else:
        raise HTTPError(http.BAD_REQUEST)
