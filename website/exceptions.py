from website.tokens.exceptions import TokenError

class OSFError(Exception):
    """Base class for exceptions raised by the Osf application"""
    pass


class NodeError(OSFError):
    """Raised when an action cannot be performed on a Node model"""
    pass


class NodeStateError(NodeError):
    """Raised when the Node's state is not suitable for the requested action

    Example: Node.remove_node() is called, but the node has non-deleted children
    """
    pass

class SanctionTokenError(TokenError):
    """Base class for errors arising from the user of a sanction token."""
    pass

class InvalidSanctionRejectionToken(TokenError):
    """Raised if a Sanction subclass disapproval token submitted is invalid
     or associated with another admin authorizer
    """
    message_short = "Invalid Token"
    message_long = "This disapproval link is invalid. Are you logged into the correct account?"

class InvalidSanctionApprovalToken(TokenError):
    """Raised if a Sanction subclass approval token submitted is invalid
     or associated with another admin authorizer
    """
    message_short = "Invalid Token"
    message_long = "This approval link is invalid. Are you logged into the correct account?"

class UserNotAffiliatedError(OSFError):
    """Raised if a user attempts to add an institution that is not currently
    one of its affiliations.
    """
    message_short = "User not affiliated"
    message_long = "This user is not affiliated with this institution."
