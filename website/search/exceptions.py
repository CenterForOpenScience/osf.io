# custom exceptions for ElasticSearch

class SearchException(Exception):
    pass


class IndexNotFoundError(SearchException):
    pass


class MalformedQueryError(SearchException):
    pass

class SearchUnavailableError(SearchException):
    pass
