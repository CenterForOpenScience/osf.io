# custom exceptions for SpamAdmin
class SpamAdminException(Exception):
    pass

class SpamAssassinUnactiveException(SpamAdminException):
    pass

class MalformedQueryError(SpamAdminException):
    pass

class SearchUnavailableError(SpamAdminException):
    pass
