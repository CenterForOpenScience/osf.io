class ApplicationException(Exception):
    pass


class InvalidSchemaError(ApplicationException):
    pass


class SchemaViolationError(ApplicationException):
    pass


class KeyMissMatchError(SchemaViolationError):
    def __init__(self):
        super(KeyMissMatchError, self).__init__('Input data has either too many or too few keys')
