from furl import furl
from datetime import datetime

from framework.utils import iso8601format
from dateutil import parser

from website.project.metadata.utils import serialize_meta_schema
from website.settings import DOMAIN as OSF_DOMAIN


EMBARGO = 'embargo'
IMMEDIATE = 'immediate'


def serialize_user(user):
    return {
        'full_name': user.fullname,
        'username': user.username,
        'id': user._id
    }


# TODO: Write and use APIv2 serializer for this
def serialize_draft_registration(draft, json_safe=True):
    node_url = get_url(draft)

    embargo = get_embargo(draft, json_safe)

    return {
        'pk': draft._id,
        'initiator': serialize_user(draft.initiator),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': iso8601format(draft.datetime_initiated) if json_safe else draft.datetime_initiated,
        'updated': iso8601format(draft.datetime_updated) if json_safe else draft.datetime_updated,
        'submitted': iso8601format(draft.approval.initiation_date) if json_safe else draft.approval.initiation_date,
        'requires_approval': draft.requires_approval,
        'is_pending_approval': draft.is_pending_review,
        'is_approved': draft.is_approved,
        'is_rejected': draft.is_rejected,
        'notes': draft.notes,
        'proof_of_publication': draft.flags.get('proof_of_publication'),
        'payment_sent': draft.flags.get('payment_sent'),
        'assignee': draft.flags.get('assignee'),
        'title': draft.registration_metadata['q1']['value'],
        'embargo': embargo,
        'registered_node': node_url,
        'status': get_approval_status(draft),
        'logs': map(serialize_draft_logs, draft.status_logs),
    }


def serialize_draft_logs(log):
    return '{} on {}'.format(log.action, datetime.strftime(log.date, '%c'))


def get_url(draft):
    url = furl(OSF_DOMAIN)
    if draft.registered_node is not None:
        url.path.add(draft.registered_node.url)
        return url.url
    elif draft.branched_from is not None:
        url.path.add(draft.branched_from.url)
        return url.url
    return None


def get_embargo(draft, json_safe):
    registration_choice = draft.approval.meta.get('registration_choice', None)
    if registration_choice == EMBARGO:
        time = parser.parse(draft.approval.meta['embargo_end_date'])
        return iso8601format(time) if json_safe else time
    return IMMEDIATE


def get_approval_status(draft):
    if draft.is_approved:
        if draft.registered_node is not None:
            if draft.registered_node.is_deleted:
                return 'Approved but canceled'
            if draft.registered_node.retraction is None:
                return 'Approved and registered'
            else:
                return 'Approved but withdrawn'
        return 'Approved but not registered'
    elif draft.is_rejected:
        return 'Rejected'
    else:
        return 'Pending approval'
