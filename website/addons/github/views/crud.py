# -*- coding: utf-8 -*-

import logging

from flask import request, make_response

from website.addons.github.api import GitHub
from website.project.decorators import must_have_addon
from website.project.decorators import must_be_contributor_or_public


logger = logging.getLogger(__name__)


# TODO Add me Test me
@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_download_starball(node_addon, **kwargs):

    archive = kwargs.get('archive', 'tar')
    ref = request.args.get('sha', 'master')

    connection = GitHub.from_settings(node_addon.user_settings)
    headers, data = connection.starball(
        node_addon.user, node_addon.repo, archive, ref
    )

    resp = make_response(data)
    for key, value in headers.iteritems():
        resp.headers[key] = value

    return resp
