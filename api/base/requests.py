from rest_framework.request import Request

from osf.models import Node
from osf.models import OSFUser


class EmbeddedRequest(Request):
    """
    Creates a Request for retrieving the embedded resource.

    Enforces that the request method is 'GET' and user is the
    authorized user from the original request.
    """
    def __init__(
        self, request, parsers=None, authenticators=None,
        negotiator=None, parser_context=None, parents=None,
    ):
        self.original_user = request.user
        self.parents = parents or {Node: {}, OSFUser: {}}
        self.version = request.version

        super(EmbeddedRequest, self).__init__(
            request._request, parsers, authenticators,
            negotiator, parser_context,
        )

    @property
    def method(self):
        """
        Overrides method to be 'GET'
        """
        return 'GET'

    @property
    def user(self):
        """
        Returns the user from the original request
        """
        return self.original_user

    @property
    def auth(self):
        """
        Returns the user from the original request
        """
        return self._request.auth
