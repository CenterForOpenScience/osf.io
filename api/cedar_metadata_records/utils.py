import logging

from osf.models import BaseFileNode, CedarMetadataRecord, Node, Registration

logger = logging.getLogger(__name__)


def get_guids_related_view(obj):
    assert isinstance(
        obj, CedarMetadataRecord
    ), "object must be a CedarMetadataRecord"
    referent = obj.guid.referent
    if isinstance(referent, Node):
        return "nodes:node-detail"
    elif isinstance(referent, Registration):
        return "registrations:registration-detail"
    elif isinstance(referent, BaseFileNode):
        return "files:file-detail"
    else:
        raise NotImplementedError()


def get_guids_related_view_kwargs(obj):
    assert isinstance(
        obj, CedarMetadataRecord
    ), "object must be a CedarMetadataRecord"
    referent = obj.guid.referent
    if isinstance(referent, (Node, Registration)):
        return {"node_id": "<guid._id>"}
    elif isinstance(referent, BaseFileNode):
        return {"file_id": "<guid._id>"}
    else:
        raise NotImplementedError()


def can_view_record(user_auth, record, guid_type=None):
    permission_source = record.guid.referent

    if guid_type and not isinstance(permission_source, guid_type):
        return False

    if isinstance(permission_source, BaseFileNode):
        permission_source = permission_source.target
    elif not isinstance(permission_source, (Node, Registration)):
        return False

    if not record.is_published:
        return permission_source.can_edit(user_auth)
    return permission_source.is_public or permission_source.can_view(user_auth)


def can_create_record(user_auth, guid):
    permission_source = guid.referent

    if isinstance(permission_source, BaseFileNode):
        permission_source = permission_source.target
    elif not isinstance(permission_source, (Node, Registration)):
        return False

    return permission_source.can_edit(user_auth)
