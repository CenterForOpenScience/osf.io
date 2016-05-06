
def create_jsonschema_from_metaschema(draft):
    """
    Creates jsonschema from registration metaschema for validation
    """
    metaschema = draft.registration_schema.schema
    json_schema = {
        "type": "object",
        "description": metaschema['description'],
        "title": metaschema['title'],
        "additionalProperties": False,
        "properties": {
        }
    }
    required = []

    for page in metaschema['pages']:
        for question in page['questions']:
            values = extract_question_values(question)
            json_schema['properties'][question['qid']] = {
                "type": "object",
                "additionalProperties": False,
                "properties": values
            }

        if required:
            json_schema['required'] = required

    return json_schema


def get_object_jsonschema(question):
    """
    Returns jsonschema for nested objects within schema
    """
    object_jsonschema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {

        }
    }
    properties = question.get('properties')
    if properties:
        for property in properties:
            values = extract_question_values(property)
            object_jsonschema['properties'][property['id']] = {
                "type": "object",
                "additionalProperties": False,
                "properties": values
            }
    return object_jsonschema


def extract_question_values(question):
    """
    Pulls the types of value, comments, and extra
    """
    value = {'type': 'string'}  # Default value
    comments = COMMENTS_SCHEMA
    extra = {'type': 'array'}
    if question.get('type') == 'object':
        value = get_object_jsonschema(question)
    elif question.get('type') == 'choose':
        options = question.get('options')
        if options:
            value = get_options_jsonschema(options)
    elif question.get('type') == 'osf-upload':
        extra = OSF_UPLOAD_EXTRA_SCHEMA

    return {
        'value': value,
        'comments': comments,
        'extra': extra
    }

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
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "seenBy": {
                "type": "array",
                "items": {
                    "type": "integer"
                }
            },
            "canDelete": {"type": "boolean"},
            "created": {"type": "string"},
            "lastModified": {"type": "string"},
            "author": {"type": "string"},
            "value": {"type": "string"},
            "isOwner": {"type": "boolean"},
            "getAuthor": {"type": "string"},
            "user": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "fullname": {"type": "string"},
                    "id": {"type": "integer"}
                }
            },
            "saved": {"type": "boolean"},
            "canEdit": {"type": "boolean"},
            "isDeleted": {"type": "boolean"}
        }
    }
}
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

