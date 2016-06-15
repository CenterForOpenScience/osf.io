from website.exceptions import NodeError

class InvalidSubscriptionError(NodeError):
    """Raised if an invalid subscription is attempted. e.g. attempt to
    subscribe to an invalid target: institution, bookmark, deleted project etc.
    """
    message_short = 'Invalid Subscription'
    message_long = 'This Subscription is not valid.'
