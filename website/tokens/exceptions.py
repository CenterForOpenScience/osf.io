class TokenHandlerNotFound(Exception):

    def __init__(self, action, *args, **kwargs):
        super(TokenHandlerNotFound, self).__init__(*args, **kwargs)

        self.action = action
        # TODO(hrybacki): build up the error message

class UnsupportedSanctionHandlerKind(Exception):
    pass
