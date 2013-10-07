import bleach

def sanitize(s, **kwargs):
    return bleach.clean(s, **kwargs)

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
