def serialize_meta_schema(meta_schema):
    if not meta_schema:
        return None
    return {
        'schema_name': meta_schema.name,
        'schema_version': meta_schema.schema_version,
        'schema': meta_schema.schema
    }

def serialize_draft_registration(draft, auth=None):
    from website.profile.utils import serialize_user  # noqa
    from website.project.utils import serialize_node  # noqa

    node = draft.branched_from

    return {
        'pk': draft._id,
        'branched_from': serialize_node(draft.branched_from, auth),
        'initiator': serialize_user(draft.initiator),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': str(draft.datetime_initiated),
        'updated': str(draft.datetime_updated),
        'config': draft.config,
        'flags': draft.flags,
        'urls': {
            'edit': node.web_url_for('edit_draft_registration', draft_id=draft._id),
            'before_register': node.api_url_for('draft_before_register', draft_id=draft._id),
            'register': node.api_url_for('register_draft_registration', draft_id=draft._id),
            'register_page': node.web_url_for('draft_before_register_page', draft_id=draft._id),
            'registrations': node.web_url_for('node_registrations')
        }
    }
