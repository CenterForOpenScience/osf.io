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

class SanctionTokenError(NodeError):
    """Base class for errors arising from the user of a sanction token."""
    pass

class InvalidSanctionRejectionToken(SanctionTokenError):
    """Raised if a embargo disapproval token is not found."""
    message_short = "Invalid Token"
    message_long = "This embargo disapproval link is invalid. Are you logged into the correct account?"

class InvalidSanctionApprovalToken(SanctionTokenError):
    """Raised if a embargo disapproval token is not found."""
    message_short = "Invalid Token"
    message_long = "This embargo disapproval link is invalid. Are you logged into the correct account?"


class InvalidRetractionApprovalToken(InvalidSanctionApprovalToken):
    pass

class InvalidRetractionDisapprovalToken(InvalidSanctionRejectionToken):
    pass

class InvalidEmbargoApprovalToken(InvalidSanctionApprovalToken):
    pass

class InvalidEmbargoDisapprovalToken(InvalidSanctionRejectionToken):
    pass

class InvalidRegistrationApprovalToken(InvalidSanctionApprovalToken):
    pass

class InvalidRegistrationDisapprovalToken(InvalidSanctionRejectionToken):
    pass
