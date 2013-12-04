import bleach
import urllib


def sanitize(s, **kwargs):
    return bleach.clean(s, **kwargs)


def process_payload(data, func):
    if isinstance(data, dict):
        return {
            key: process_payload(value, func)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            process_payload(value, func)
            for value in data
        ]
    return func(data)


def prepare_payload(data):
    """Recursively quote payload.

    :param data: Payload dictionary
    :return: Quoted payload

    """
    return process_payload(data, urllib.quote_plus)


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
