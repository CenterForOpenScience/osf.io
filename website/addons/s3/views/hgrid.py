# -*- coding: utf-8 -*-

from flask import request
from urllib import unquote
import httplib as http

from framework.exceptions import HTTPError

from website.util import rubeus
from website.project.decorators import (
    must_be_contributor_or_public, must_have_addon,
)
from website.addons.s3.api import S3Wrapper
from website.addons.s3.utils import wrapped_key_to_json


def s3_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no bucket
    if not node_settings.bucket or not node_settings.user_settings or not node_settings.user_settings.has_auth:
        return

    node = node_settings.owner
    return [
        rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
        )
    ]


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_hgrid_data_contents(auth, node_addon, **kwargs):
    node = node_addon.owner
    path = unquote(kwargs.get('path', None)) + '/' if kwargs.get('path', None) else None

    can_edit = node.can_edit(auth) and not node.is_registration
    can_view = node.can_view(auth)

    s3wrapper = S3Wrapper.from_addon(node_addon)

    if s3wrapper is None:
        raise HTTPError(http.BAD_REQUEST)

    files = []

    key_list = s3wrapper.get_wrapped_keys_in_dir(path)
    key_list.extend(s3wrapper.get_wrapped_directories_in_dir(path))

    for key in key_list:
        temp_file = wrapped_key_to_json(key, node)
        temp_file['addon'] = 's3'
        temp_file['permissions'] = {
            'edit': can_edit,
            'view': can_view
        }
        files.append(temp_file)

    return files


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_dummy_folder(auth, node_addon, **kwargs):
    data = request.args.to_dict()
    return s3_hgrid_data(node_addon, auth, **data)
