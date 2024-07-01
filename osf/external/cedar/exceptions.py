class CedarClientError(Exception):

    def __init__(self, reason='Cedar API Error'):
        super().__init__(reason)
        self.reason = reason


class CedarClientRequestError(CedarClientError):
    pass


class CedarClientResponseError(CedarClientError):
    pass
