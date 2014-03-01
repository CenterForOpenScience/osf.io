import os
import json
import datetime
import httplib as http

from framework.flask import secure_filename

from framework import request
from framework.exceptions import HTTPError

from website.project import decorators
from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.project.views.node import _view_project
from website.project.views.file import get_cache_content

from website.addons.figshare import settings as figshare_settings

from ..api import Figshare

# Helpers


def figshare_log_file_added(node, auth, path):
    node.add_log(
        action='figshare_file_added',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'path': os.path.join(path, filename),
            'urls': {
                'view': view_url,
                'download': download_url,
            },
            'github': {
                'id': '',
                'type': ''
            },
        },
        auth=auth,
        log_date=now,
    )


# ----------------- PROJECTS ---------------
# PROJECTS: C
@decorators.must_be_contributor
@decorators.must_have_addon('figshare', 'node')
def figshare_create_project(*args, **kwargs):
    # TODO implement me
    pass

# PROJECTS: R


@decorators.must_be_contributor
@decorators.must_have_addon('figshare', 'node')
def figshare_get_project(*args, **kwargs):
    # TODO implement me
    node, figshare = figshare_get_context(**kwargs)
    pass

# PROJECTS: U


@decorators.must_be_contributor
@decorators.must_have_addon('figshare', 'node')
def figshare_add_article_to_project(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')

    project_id = kwargs.get('project_id') or None
    if project_id is None:
        raise HTTPError(http.BAD_REQUEST)

    article_id = kwargs.get('aid') or None

    article = None
    connect = Figshare.from_settings(figshare.user_settings)
    if not article_id:
        article = file_as_article(figshare)

    connect.add_article_to_project(figshare, article['article_id'], project_id)

# PROJECTS: D


@decorators.must_be_contributor
@decorators.must_have_addon('figshare', 'node')
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


def file_as_article(upload):
    filename = secure_filename(upload.filename)
    article = {
        'title': filename,
        'files': [upload]
    }
    return article


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
def figshare_upload_file_as_article(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    figshare = node.get_addon('figshare')
    upload = request.files['file']

    project_id = kwargs.get('project_id') or None
    if project_id is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)
    article = connect.create_article(figshare, file_as_article(upload))

    return connect.upload_file(node, figshare, article['items'][0], upload)

# ARTICLES: D


def figshare_delete_article(*args, **kwargs):
    # TODO implement me?
    pass

# ----------------- FILES --------------------
# FILES: C


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
def figshare_upload_file_to_article(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    user = auth.user
    figshare = node.get_addon('figshare')

    path = kwargs.get('path', '')

    article = kwargs.get('aid') or None

    connect = Figshare.from_settings(figshare.user_settings)

    if not article:
        article = connect.create_article()

    upload = request.files['file']

    return connect.upload_file(
        node,
        figshare,
        article,
        upload
    )

# FILES: R


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_view_file(*args, **kwargs):
    auth = kwargs['auth']
    user = auth.user
    node = kwargs['node'] or kwargs['project']
    node_settings = kwargs['node_addon']

    article_id = kwargs.get('aid') or None
    file_id = kwargs.get('fid') or None

    if article_id is None or file_id is None:
        raise HTTPError(http.NOT_FOUND)

    connect = Figshare.from_settings(node_settings.user_settings)

    article = connect.article(node_settings, article_id)

    found = False
    for f in article['items'][0]['files']:
        if f['id'] == int(file_id):
            found = f
            break
    if not f:
        raise HTTPError(http.NOT_FOUND)
    private = not(article['items'][0]['status'] == 'Public')

    version_url = "http://figshare.com/articles/{filename}/{file_id}".format(
        filename=article['items'][0]['title'], file_id=article['items'][0]['article_id'])

    download_url = node.api_url + \
        'download/article/{aid}/file/{fid}'.format(aid=article_id, fid=file_id)
    render_url = node.api_url + \
        'figshare/render/article/{aid}/file/{fid}'.format(aid=article_id, fid=file_id)

    cache_file = get_cache_file(
        article_id, file_id
    )
    rendered = get_cache_content(node_settings, cache_file)
    filename = found['name']

    if private:
        rendered = "Since this FigShare file is unpublished we cannot render it. In order to access this content you will need to log into the <a href='{url}'>FigShare page</a> and view it there.".format(
            url='http://figshare.com/')
    elif rendered is None:
        filename, size, filedata = connect.get_file(node_settings, found)
        if figshare_settings.MAX_RENDER_SIZE is not None and size > figshare_settings.MAX_RENDER_SIZE:
            rendered = "File too large to render; <a href='{url}'>download file</a> to view it".format(
                url=found.get('download_url'))
        else:
            rendered = get_cache_content(
                node_settings, cache_file, start_render=True,
                file_path=filename, file_content=filedata, download_path=download_url)

    rv = {
        'file_name': filename,
        'render_url': render_url,
        'rendered': rendered,
        'download_url': found.get('download_url'),
        'file_status': article['items'][0]['status'],
        'file_version': article['items'][0]['version'],
        'version_url': version_url
    }
    rv.update(_view_project(node, auth, primary=True))
    return rv


def get_cache_file(article_id, file_id):
    return '{1}_{0}.html'.format(article_id, file_id)

# FILES: D


@decorators.must_be_contributor_or_public
@decorators.must_have_addon('figshare', 'node')
def figshare_delete_file(*args, **kwargs):

    node = kwargs['node'] or kwargs['project']
    user = kwargs['user']
    figshare = node.get_addon('figshare')

    file_id = kwargs.get('fid', '')
    article_id = kwargs.get('aid', '')

    if file_id is None or article_id is None:
        raise HTTPError(http.BAD_REQUEST)

    connect = Figshare.from_settings(figshare.user_settings)

    return connect.delete_file(node, figshare, article_id, file_id)


@must_be_contributor_or_public
@must_have_addon('figshare', 'node')
def figshare_get_rendered_file(*args, **kwargs):
    node_settings = kwargs['node_addon']
