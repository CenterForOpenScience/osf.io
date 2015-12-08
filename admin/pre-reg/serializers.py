from framework.utils import iso8601format
from website.project.metadata.utils import serialize_meta_schema


# TODO: Write and use APIv2 serializer for this
def serialize_draft_registration(draft):
    from website.profile.utils import serialize_user  # noqa

    return {
        'pk': draft._id,
        'initiator': serialize_user(draft.initiator, full=True),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': iso8601format(draft.datetime_initiated),
        'updated': iso8601format(draft.datetime_updated),
        'flags': draft.flags,
        'requires_approval': draft.requires_approval,
        'is_pending_approval': draft.is_pending_review,
        'is_approved': draft.is_approved,
        'notes': draft.notes
    }
