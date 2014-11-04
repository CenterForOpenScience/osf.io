class ApplicationException(Exception):
    pass


class InvalidSchemaError(ApplicationException):
    pass


class SchemaViolationError(ApplicationException):
    pass


class AdditionalKeysError(SchemaViolationError):
    pass
