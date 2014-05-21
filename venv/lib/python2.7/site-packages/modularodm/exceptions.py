class ModularOdmException(Exception):
    """ base class from which all exceptions raised by modularodm should inherit
    """
    pass


class QueryException(ModularOdmException):
    """ base class for exceptions raised from query parsing or execution"""
    pass


class MultipleResultsFound(QueryException):
    """ Raised when multiple results match the passed query, and only a single
    object may be returned """
    pass


class NoResultsFound(QueryException):
    """ Raised when no results match the passed query, but one or more results
    must be returned. """
    pass


class ValidationError(ModularOdmException):
    """ Base class for exceptions raised during validation. Should not raised
    directly. """
    pass


class ValidationTypeError(ValidationError, TypeError):
    """ Raised during validation if explicit type check failed """
    pass


class ValidationValueError(ValidationError, ValueError):
    """ Raised during validation if the value of the input is unacceptable, but
     the type is correct """
    pass


class ImproperConfigurationError(ModularOdmException):
    """Raised if configuration options are not set correctly."""
    pass

class DatabaseError(ModularOdmException):
    '''Raised when execution of a database operation fails.'''
    pass
