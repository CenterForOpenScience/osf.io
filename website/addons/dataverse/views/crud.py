# -*- coding: utf-8 -*-
import httplib
import logging
import datetime

from flask import request

from framework.exceptions import HTTPError
from website.addons.dataverse.client import (
    publish_dataset, get_dataset, get_dataverse, connect_from_settings_or_401,
    publish_dataverse,
)
from website.project.decorators import must_have_permission
from website.project.decorators import must_not_be_registration
from website.project.decorators import must_have_addon

logger = logging.getLogger(__name__)


@must_have_permission('write')
@must_not_be_registration
@must_have_addon('dataverse', 'node')
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
