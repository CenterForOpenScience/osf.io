import logging

from osf.models import BaseFileNode, CedarMetadataRecord, Node, Registration

logger = logging.getLogger(__name__)


def get_guids_related_view(obj):
    assert isinstance(obj, CedarMetadataRecord), 'object must be a CedarMetadataRecord'
    referent = obj.guid.referent
    if isinstance(referent, Node):
        return 'nodes:node-detail'
    elif isinstance(referent, Registration):
        return 'registrations:registration-detail'
    elif isinstance(referent, BaseFileNode):
        return 'files:file-detail'
    else:
        raise NotImplementedError()


def get_guids_related_view_kwargs(obj):
    assert isinstance(obj, CedarMetadataRecord), 'object must be a CedarMetadataRecord'
    referent = obj.guid.referent
    if isinstance(referent, (Node, Registration)):
        return {'node_id': '<guid._id>'}
    elif isinstance(referent, BaseFileNode):
        return {'file_id': '<guid._id>'}
    else:
        raise NotImplementedError()
