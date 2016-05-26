class TokenError(Exception):
    pass


class TokenHandlerNotFound(TokenError):

    def __init__(self, action, *args, **kwargs):
        super(TokenHandlerNotFound, self).__init__(*args, **kwargs)

        self.action = action


class UnsupportedSanctionHandlerKind(Exception):
    pass
