# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from framework.exceptions import HTTPError
from osf.models import NodeLog

from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
)
from website.identifiers.utils import get_or_create_identifiers
from osf.utils.permissions import ADMIN


@must_be_valid_project
@must_have_permission(ADMIN)
def node_identifiers_post(auth, node, **kwargs):
    """Create identifier pair for a node. Node must be a public registration.
    """
    # TODO this functionality exists in APIv2. When front end is entirely using
    # v2 for minting DOI's, remove this view.
    if not node.is_public or node.is_retracted:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    if node.get_identifier('doi') or node.get_identifier('ark'):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    try:
        identifiers = get_or_create_identifiers(node)
    except HTTPError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    for category, value in identifiers.items():
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
    return identifiers, http_status.HTTP_201_CREATED
