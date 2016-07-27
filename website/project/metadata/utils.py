from framework import utils

from website.settings import PREREG_ADMIN_TAG
from website.util import permissions as osf_permissions

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

def create_jsonschema_from_metaschema(metaschema, required_fields=False, is_reviewer=False):
    """
    Creates jsonschema from registration metaschema for validation.

    Reviewer schemas only allow comment fields.
    """
    json_schema = base_metaschema(metaschema)
    required = []

    for page in metaschema['pages']:
        for question in page['questions']:
            if is_required(question) and required_fields:
                required.append(question['qid'])
            json_schema['properties'][question['qid']] = {
                'type': 'object',
                'additionalProperties': False,
                'properties': extract_question_values(question, required_fields, is_reviewer)
            }
            if required_fields:
                json_schema['properties'][question['qid']]['required'] = ['value']

        if required and required_fields:
            json_schema['required'] = required

    return json_schema

def get_object_jsonschema(question, required_fields, is_reviewer):
    """
    Returns jsonschema for nested objects within schema
    """
    object_jsonschema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {

        }
    }
    required = []
    properties = question.get('properties')
    if properties:
        for property in properties:
            if property.get('required', False) and required_fields:
                required.append(property['id'])
            values = extract_question_values(property, required_fields, is_reviewer)
            object_jsonschema['properties'][property['id']] = {
                'type': 'object',
                'additionalProperties': False,
                'properties': values
            }
            if required_fields:
                object_jsonschema['properties'][property['id']]['required'] = ['value']
    if required_fields and is_required(question):
        object_jsonschema['required'] = required

    return object_jsonschema

def extract_question_values(question, required_fields, is_reviewer):
    """
    Pulls structure for 'value', 'comments', and 'extra' items
    """
    response = {
        'value': {'type': 'string'},
        'comments': COMMENTS_SCHEMA,
        'extra': {'type': 'array'}
    }
    if question.get('type') == 'object':
        response['value'] = get_object_jsonschema(question, required_fields, is_reviewer)
    elif question.get('type') == 'choose':
        options = question.get('options')
        if options:
            response['value'] = get_options_jsonschema(options)
    elif question.get('type') == 'osf-upload':
        response['extra'] = OSF_UPLOAD_EXTRA_SCHEMA

    if is_reviewer:
        del response['extra']
        if not question.get('type') == 'object':
            del response['value']

    return response

def is_required(question):
    """
    Returns True if metaschema question is required.
    """
    required = question.get('required', False)
    if not required:
        properties = question.get('properties', False)
        if properties and isinstance(properties, list):
            for item, property in enumerate(properties):
                if isinstance(property, dict) and property.get('required', False):
                    required = True
                    break
    return required

def get_options_jsonschema(options):
    """
    Returns multiple choice options for schema questions
    """
    for item, option in enumerate(options):
        if isinstance(option, dict) and option.get('text'):
            options[item] = option.get('text')
    value = {'enum': options}
    return value

OSF_UPLOAD_EXTRA_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'data': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'kind': {'type': 'string'},
                    'contentType': {'type': 'string'},
                    'name': {'type': 'string'},
                    'extra': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'downloads': {'type': 'integer'},
                            'version': {'type': 'integer'},
                            'checkout': {'type': 'string'},
                            'hashes': {
                                'type': 'object',
                                'additionalProperties': False,
                                'properties': {
                                    'sha256': {'type': 'string'},
                                    'md5': {'type': 'string'}
                                }
                            }
                        }
                    },
                    'materialized': {'type': 'string'},
                    'modified': {'type': 'string'},
                    'nodeId': {'type': 'string'},
                    'etag': {'type': 'string'},
                    'provider': {'type': 'string'},
                    'path': {'type': 'string'},
                    'size': {'type': 'integer'}
                }
            },
            'sha256': {'type': 'string'},
            'selectedFileName': {'type': 'string'},
            'nodeId': {'type': 'string'},
            'viewUrl': {'type': 'string'}
        }
    }
}

COMMENTS_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'seenBy': {
                'type': 'array',
                'items': {
                    'type': 'integer'
                }
            },
            'canDelete': {'type': 'boolean'},
            'created': {'type': 'string'},
            'lastModified': {'type': 'string'},
            'author': {'type': 'string'},
            'value': {'type': 'string'},
            'isOwner': {'type': 'boolean'},
            'getAuthor': {'type': 'string'},
            'user': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'fullname': {'type': 'string'},
                    'id': {'type': 'integer'}
                }
            },
            'saved': {'type': 'boolean'},
            'canEdit': {'type': 'boolean'},
            'isDeleted': {'type': 'boolean'}
        }
    }
}

def base_metaschema(metaschema):
    json_schema = {
        'type': 'object',
        'description': metaschema['description'],
        'title': metaschema['title'],
        'additionalProperties': False,
        'properties': {
        }
    }
    return json_schema

def is_prereg_admin(user):
    """
    Returns true if user has reviewer permissions
    """
    if user is not None:
        return PREREG_ADMIN_TAG in getattr(user, 'system_tags', [])
    return False

def is_prereg_admin_not_project_admin(request, draft):
    """
    Returns true if user is prereg admin, but not admin on project
    """
    user = request.user
    is_project_admin = draft.branched_from.has_permission(user, osf_permissions.ADMIN)

    return is_prereg_admin(user) and not is_project_admin
