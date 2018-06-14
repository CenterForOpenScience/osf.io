class SearchException(Exception):
    pass


class IndexNotFoundError(SearchException):
    pass


class MalformedQueryError(SearchException):
    pass


class BulkUpdateError(SearchException):
    pass


class SearchUnavailableError(SearchException):
    pass


class SearchDisabledException(SearchUnavailableError):
    pass
