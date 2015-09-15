# This should be the browser for dryad

from website.addons.dryad import api

import httplib
import logging
import datetime

from flask import request
from framework.flask import redirect

from framework.exceptions import HTTPError
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

logger = logging.getLogger(__name__)

@must_have_addon('wiki', 'node')
def dryad_browser(**kwargs):
    node = kwargs['node'] or kwargs['project']
    dryad = node.get_addon('dryad')

    ret = {}
    ret.update(dryad.config.to_json() )
    """
    ret = {
        'complete': True,
        'wiki_content': unicode(wiki_html) if wiki_html else None,
        'wiki_content_url': node.api_url_for('wiki_page_content', wname='home'),
        'use_python_render': use_python_render,
        'more': more,
        'include': False,
    }
    ret.update(wiki.config.to_json())
    return ret
    """
    return ret
    #return redirect(node.web_url_for('project_wiki_view', wname='home', _guid=True))


"""
def dataverse_publish_dataset(node_addon, auth, **kwargs):
    node = node_addon.owner
    publish_both = request.json.get('publish_both', False)

    now = datetime.datetime.utcnow()

    try:
        connection = connect_from_settings_or_401(node_addon)
    except HTTPError as error:
        if error.code == httplib.UNAUTHORIZED:
            connection = None
        else:
            raise

    dataverse = get_dataverse(connection, node_addon.dataverse_alias)
    dataset = get_dataset(dataverse, node_addon.dataset_doi)

    if publish_both:
        publish_dataverse(dataverse)
    publish_dataset(dataset)

    # Add a log
    node.add_log(
        action='dataverse_dataset_published',
        params={
            'project': node.parent_id,
            'node': node._primary_key,
            'dataset': dataset.title,
        },
        auth=auth,
        log_date=now,
    )

    return {'dataset': dataset.title}, httplib.OK
"""