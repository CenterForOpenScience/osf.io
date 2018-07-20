import json

from admin.nodes.serializers import serialize_node


def serialize_preprint(preprint):

    return {
        'id': preprint._id,
        'date_created': preprint.created,
        'modified': preprint.modified,
        'provider': preprint.provider,
        'node': serialize_node(preprint.node),
        'is_published': preprint.is_published,
        'date_published': preprint.date_published,
        'subjects': preprint.subjects.all(),
        'spam_status': preprint.spam_status,
        'spam_pro_tip': preprint.spam_pro_tip,
        'spam_data': json.dumps(preprint.spam_data, indent=4),
    }
