import bleach
from framework.exceptions import SanitizeError


def sanitize(s, **kwargs):
    return bleach.clean(s, **kwargs)


def _sanitize(value):
    """Sanitize a single value; raise SanitizeError if sanitizing fails.

    """
    if value is not None and value != sanitize(value):
        raise SanitizeError('Value "{0}" not allowed'.format(value))


def sanitize_payload(data):
    """Sanitize a payload dictionary; raise SanitizeError if sanitizing fails
    for any value or nested value.
    """
    for key, value in data.items():
        if isinstance(value, list):
            for item in value:
                _sanitize(item)
        else:
            _sanitize(value)


def jsonify(form):
    """Cast WTForm to JSON object.

    """
    return {
        'form': [
            {
                'id': field.id,
                'label': str(field.label),
                'html': str(field),
            }
            for field in form
        ]
    }
