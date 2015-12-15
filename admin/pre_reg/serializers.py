from framework.utils import iso8601format

from website.project.metadata.utils import serialize_meta_schema


def serialize_user(user):
    return {
        'full_name': user.fullname,
        'username': user.username,
        'id': user._id
    }

# TODO: Write and use APIv2 serializer for this
def serialize_draft_registration(draft, json_safe=True):

    return {
        'pk': draft._id,
        'initiator': serialize_user(draft.initiator),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': iso8601format(draft.datetime_initiated) if json_safe else draft.datetime_initiated,
        'updated': iso8601format(draft.datetime_updated) if json_safe else draft.datetime_updated,
        'requires_approval': draft.requires_approval,
        'is_pending_approval': draft.is_pending_review,
        'is_approved': draft.is_approved,
        'is_rejected': draft.is_rejected,
        'notes': draft.notes,
        'proof_of_publication': draft.flags.get('proof_of_publication'),
        'payment_sent': draft.flags.get('payment_sent'),
        'assignee': draft.flags.get('assignee'),
        'title': draft.registration_metadata['q1']['value'],
    }
