from rest_framework.request import Request


class EmbeddedRequest(Request):
    """
    Creates a Request for retrieving the embedded resource.

    Enforces that the request method is 'GET' and user is the
    authorized user from the original request.
    """
    def __init__(self, request, parsers=None, authenticators=None,
                 negotiator=None, parser_context=None):
        self.original_user = request.user
        super(EmbeddedRequest, self).__init__(request, parsers, authenticators,
                                              negotiator, parser_context)

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
