from __future__ import unicode_literals

import httplib as http

from flask import request

from framework.guid.model import Metadata
from framework.exceptions import HTTPError

from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_not_be_registration, must_be_contributor_or_public
)
from website.addons.app.utils import create_orphaned_metadata

# GET
@must_be_contributor_or_public
@must_have_addon('app', 'node')
def get_metadata(node_addon, guid, **kwargs):
    try:
        return node_addon.get_data(guid)
    except TypeError:
        pass

    try:
        return Metadata.load(guid).to_json()
    except TypeError:
        raise HTTPError(http.NOT_FOUND)


# POST, PUT
@must_have_permission('write')
@must_have_addon('app', 'node')
def add_metadata(node_addon, guid, **kwargs):
    metadata = request.json

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)
    try:
        node_addon.attach_data(guid, metadata)
        node_addon.save()
    except TypeError:
        raise HTTPError(http.BAD_REQUEST)


# DELETE
@must_have_permission('admin')
@must_have_addon('app', 'node')
def delete_metadata(node_addon, guid, **kwargs):
    key = request.args.get('key', None)

    if key:
        key = key.split(',')

    metastore = Metadata.load(guid)
    # Note: You cannot delete keys from orphan metadata
    if metastore:
        Metadata.remove_one(metastore, True)
        return HTTPError(http.NO_CONTENT)

    try:
        node_addon.delete_data(guid, keys=key)
    except KeyError:
        raise HTTPError(http.BAD_REQUEST)

    if key:
        return {
            'deleted': key
        }, http.OK

    return HTTPError(http.NO_CONTENT)


@must_have_permission('write')
@must_have_addon('app', 'node')
def create_ophan_metadata(node_addon, **kwargs):
    metadata = request.json

    if not metadata:
        raise HTTPError(http.BAD_REQUEST)
    try:
        metastore = create_ophan_metadata(node_addon, metadata)
        metastore.save()
        node_addon.save()
    except TypeError:
        raise HTTPError(http.BAD_REQUEST)
