from urllib.parse import quote, unquote

from framework.utils import sanitize_html


# TODO: Test me @jmcarp

def sanitize(s, **kwargs):
    return sanitize_html(s, **kwargs)


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
