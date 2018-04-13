# -*- coding: utf-8 -*-
import httplib as http

from framework.exceptions import HTTPError
from osf.models import NodeLog

from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
)
from website.identifiers.utils import request_identifiers_from_datacite
from osf.utils.permissions import ADMIN


@must_be_valid_project
@must_have_permission(ADMIN)
def node_identifiers_post(auth, node, **kwargs):
    """Create identifier pair for a node. Node must be a public registration.
    """
    if not node.is_public or node.is_retracted:
        raise HTTPError(http.BAD_REQUEST)
    if node.get_identifier('doi') or node.get_identifier('ark'):
        raise HTTPError(http.BAD_REQUEST)
    try:
        doi, ark = request_identifiers_from_datacite(node)
        identifiers = {'doi': doi, 'ark': ark}
    except HTTPError:
        raise HTTPError(http.BAD_REQUEST)
    for category, value in identifiers.iteritems():
        node.set_identifier_value(category, value)
    node.add_log(
        NodeLog.EXTERNAL_IDS_ADDED,
        params={
            'parent_node': node.parent_id,
            'node': node._id,
            'identifiers': identifiers,
        },
        auth=auth,
    )
    return identifiers, http.CREATED
