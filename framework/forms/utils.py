import bleach

def sanitize(s, **kwargs):
    return bleach.clean(s, **kwargs)
