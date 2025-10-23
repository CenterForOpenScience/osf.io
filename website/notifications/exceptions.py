from osf.exceptions import OSFError

class InvalidSubscriptionError(OSFError):
    """Raised if an invalid subscription is attempted. e.g. attempt to
    subscribe to an invalid target: institution, bookmark, deleted project etc.
    """
    pass
