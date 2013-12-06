import bleach
import urllib


def sanitize(s, **kwargs):
    return bleach.clean(s, **kwargs)


def process_data(data, func):
    if isinstance(data, dict):
        return {
            key: process_data(value, func)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            process_data(item, func)
            for item in data
        ]
    return func(data)


def _quote(value):
    return urllib.quote(value, safe=' ')


def process_payload(data):
    return process_data(data, _quote)


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
