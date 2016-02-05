from framework import utils

def serialize_initiator(initiator):
    return {
        'fullname': initiator.fullname,
        'id': initiator._id
    }

def serialize_meta_schema(meta_schema):
    if not meta_schema:
        return None
    return {
        'id': meta_schema._id,
        'schema_name': meta_schema.name,
        'schema_version': meta_schema.schema_version,
        'schema': meta_schema.schema,
        'fulfills': meta_schema.fulfills,
        'requires_approval': meta_schema.requires_approval,
        'requires_consent': meta_schema.requires_consent,
        'messages': meta_schema.messages
    }

def serialize_meta_schemas(meta_schemas):
    return [serialize_meta_schema(schema) for schema in (meta_schemas or [])]

def serialize_draft_registration(draft, auth=None):
    from website.project.utils import serialize_node  # noqa

    node = draft.branched_from

    return {
        'pk': draft._id,
        'branched_from': serialize_node(node, auth),
        'initiator': serialize_initiator(draft.initiator),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': utils.iso8601format(draft.datetime_initiated),
        'updated': utils.iso8601format(draft.datetime_updated),
        'flags': draft.flags,
        'urls': {
            'edit': node.web_url_for('edit_draft_registration_page', draft_id=draft._id),
            'submit': node.api_url_for('submit_draft_for_review', draft_id=draft._id),
            'before_register': node.api_url_for('project_before_register'),
            'register': node.api_url_for('register_draft_registration', draft_id=draft._id),
            'register_page': node.web_url_for('draft_before_register_page', draft_id=draft._id),
            'registrations': node.web_url_for('node_registrations')
        },
        'requires_approval': draft.requires_approval,
        'is_pending_approval': draft.is_pending_review,
        'is_approved': draft.is_approved,
    }
