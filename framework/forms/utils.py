from urllib.parse import quote, unquote

from framework.utils import sanitize_html


# TODO: Test me @jmcarp

def sanitize(s, **kwargs):
    return sanitize_html(s, **kwargs)


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


def process_payload(data):
    return process_data(
        data,
        lambda value: quote(value.encode('utf-8') if value else '', safe=' ')
    )


def unprocess_payload(data):
    return process_data(
        data,
        lambda value: unquote(value.encode('utf-8') if value else '')
    )


def jsonify(form):
    """Cast WTForm to JSON object.

    """
    return {
        'form': [
            {
                'id': field.id,
                'label': str(field.label),
                'html': str(field),
                'description': str(field.description)
            }
            for field in form
        ]
    }
