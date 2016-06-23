"""Views for the node settings page."""
# -*- coding: utf-8 -*-
import httplib as http

from flask import request
from modularodm.exceptions import ValidationError

from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_not_be_registration,
    must_be_valid_project)

from website.addons.forward.utils import serialize_settings


@must_be_valid_project
@must_have_addon('forward', 'node')
def forward_config_get(node_addon, **kwargs):
    return serialize_settings(node_addon)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('forward', 'node')
def forward_config_put(auth, node_addon, **kwargs):
    """Set configuration for forward node settings, adding a log if URL has
    changed.

    :param-json str url: Forward URL
    :raises: HTTPError(400) if values missing or invalid

    """
    try:
        node_addon.url = request.json['url']
        node_addon.label = request.json.get('label')
    except (KeyError, TypeError, ValueError):
        raise HTTPError(http.BAD_REQUEST)

    # Save settings and get changed fields; crash if validation fails
    try:
        saved_fields = node_addon.save()
    except ValidationError:
        raise HTTPError(http.BAD_REQUEST)

    # Log change if URL updated
    if 'url' in saved_fields:
        node_addon.owner.add_log(
            action='forward_url_changed',
            params=dict(
                node=node_addon.owner._id,
                project=node_addon.owner.parent_id,
                forward_url=node_addon.url,
            ),
            auth=auth,
            save=True,
        )

    return {}
