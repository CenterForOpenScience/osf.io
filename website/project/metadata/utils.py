from website.profile.utils import serialize_user
from website.project.utils import serialize_node

def serialize_meta_schema(meta_schema):
    if not meta_schema:
        return None
    return {
        'schema_name': meta_schema.name,
        'schema_version': meta_schema.schema_version,
        'schema': meta_schema.schema
    }

def serialize_draft_registration(draft, auth=None):
    ret = {
        key: getattr(draft, key)
        for key in ['title', 'description']
    }
    ret.update({
        'pk': draft._id,
        'branched_from': serialize_node(draft.branched_from, auth),
        'initiator': serialize_user(draft.initiator),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': str(draft.datetime_initiated),
        'updated': str(draft.datetime_updated),
        'completion': 50  # TODO
    })
    return ret
