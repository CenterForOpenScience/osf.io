"""Views for the node settings page."""
# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from flask import request
from osf.exceptions import ValidationValueError
from osf.utils.permissions import WRITE
from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon,
    must_have_permission,
    must_not_be_registration,
    must_be_valid_project)

from addons.forward.utils import serialize_settings


@must_be_valid_project
@must_have_addon('forward', 'node')
def forward_config_get(node, node_addon, **kwargs):
    res = serialize_settings(node_addon)
    res.update({'is_registration': node.is_registration})
    return res


@must_have_permission(WRITE)
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
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Save settings and get changed fields; crash if validation fails
    try:
        dirty_fields = node_addon.get_dirty_fields()
        node_addon.save(request=request)
    except ValidationValueError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Log change if URL updated
    if 'url' in dirty_fields:
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
