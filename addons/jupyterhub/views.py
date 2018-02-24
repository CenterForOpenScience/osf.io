# -*- coding: utf-8 -*-
import httplib
from flask import request
import logging

from . import settings
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
)

logger = logging.getLogger(__name__)


@must_be_contributor_or_public
@must_have_addon('jupyterhub', 'node')
def jupyterhub_widget(**kwargs):
    node = kwargs['node'] or kwargs['project']
    jupyterhub = node.get_addon('jupyterhub')

    ret = {
        'complete': True,
        'include': False,
    }
    ret.update(jupyterhub.config.to_json())
    return ret

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon('jupyterhub', 'node')
def jupyterhub_get_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    jupyterhub = node.get_addon('jupyterhub')
    return {'data': [dict(zip(['name', 'base_url'], s))
                     for s in jupyterhub.get_services()]}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon('jupyterhub', 'node')
def jupyterhub_set_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    jupyterhub = node.get_addon('jupyterhub')
    try:
        service_list = request.json['service_list']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)
    logger.info('Service: {}'.format(service_list))
    jupyterhub.set_services([(s['name'], s['base_url']) for s in service_list])
    return {}

@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('jupyterhub', 'node')
def jupyterhub_get_services(**kwargs):
    node = kwargs['node'] or kwargs['project']
    jupyterhub = node.get_addon('jupyterhub')
    return {'data': [dict(zip(['name', 'base_url'], s))
                     for s in jupyterhub.get_services() + settings.SERVICES]}
