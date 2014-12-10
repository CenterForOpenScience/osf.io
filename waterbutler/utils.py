from functools import wraps


def lazyproperty(func):
    @property
    @wraps(func)
    def _lazyprop(*args, **kwargs):
        self = args[0]
        attrname = '__{0}'.format(func.__name__)
        try:
            return getattr(self, attrname)
        except AttributeError:
            setattr(self, attrname, func(*args, **kwargs))
            return _lazyprop(*args, **kwargs)
    return _lazyprop
