class UnmockedError(Exception):
    def __init__(self):
        super(Exception, self).__init__(
            'No mocking exists, and real connections are '
            'not allowed.'
        )