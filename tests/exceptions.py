class UnmockedError(Exception):
    def __init__(self, message='No requests mocking exists, \
real connections are not allowed.'):
        super().__init__(message)
