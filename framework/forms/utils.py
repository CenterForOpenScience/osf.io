import bleach


def sanitize(s):
    return bleach.clean(s)