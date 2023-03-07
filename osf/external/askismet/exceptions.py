class AkismetClientError(Exception):

    def __init__(self, reason):
        super(AkismetClientError, self).__init__(reason)
        self.reason = reason
