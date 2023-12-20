class CedarClientError(Exception):

    def __init__(self, reason):
        super(CedarClientError, self).__init__(reason)
        self.reason = reason


class CedarClientRequestError(CedarClientError):
    pass


class CedarClientResponseError(CedarClientError):
    pass
