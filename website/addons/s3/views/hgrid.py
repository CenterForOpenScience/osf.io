# -*- coding: utf-8 -*-
import os
import httplib as http
from urllib import unquote

from flask import request

from boto.s3.key import Key

from framework.exceptions import HTTPError

from website.util import rubeus
from website.addons.s3.api import S3Wrapper
from website.addons.s3.utils import build_urls
from website.project.decorators import must_be_contributor_or_public, must_have_addon


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

    path = kwargs.get('path')

    if path:
        path = unquote(path) + '/'

    can_view = node.can_view(auth)
    can_edit = node.can_edit(auth) and not node.is_registration

    s3wrapper = S3Wrapper.from_addon(node_addon)

    if s3wrapper is None:
        raise HTTPError(http.BAD_REQUEST)

    def clean_name(key):
        if isinstance(key, Key):
            if path:
                return key.name.replace(path, '')
            return key.name

        if path:
            return key.name.replace(path, '')[:-1]
        return key.name[:-1]

    return [
        {
            'name': clean_name(key),
            'addon': 's3',
            'permissions': {
                'edit': can_edit,
                'view': can_view
            },
            rubeus.KIND: rubeus.FILE if isinstance(key, Key) else rubeus.FOLDER,
            'ext': os.path.splitext(key.name)[1],
            'urls': build_urls(node, key.name.encode('utf-8'))
        }
        for key
        in s3wrapper.bucket.list(prefix=path, delimiter='/')
        if key.name != path
    ]


@must_be_contributor_or_public
@must_have_addon('s3', 'node')
def s3_dummy_folder(**kwargs):
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()
    return s3_hgrid_data(node_settings, auth, **data)
