# -*- coding: utf-8 -*-

import httplib as http

from flask import request
from framework.exceptions import HTTPError

from website.project import decorators  # noqa
from website.project.decorators import must_be_contributor_or_public, must_be_contributor  # noqa

from ..api import Figshare


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
