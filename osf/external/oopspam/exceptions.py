class OOPSpamClientError(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason
