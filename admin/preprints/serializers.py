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
        'pending_withdrawal': preprint.has_pending_withdrawal_request,
        'withdrawal_request': preprint.requests.first() if preprint.has_withdrawal_request else {},
    }


def serialize_withdrawal_request(request):

    return {
        'id': request._id,
        'created': request.created,
        'modified': request.modified,
        'creator': request.creator,
        'comment': request.comment,
        'preprint': serialize_preprint(request.target),
        'state': request.machine_state,
        'date_last_transitioned': request.date_last_transitioned,
    }
