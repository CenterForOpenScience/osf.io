from github3 import GitHubError

class ApiError(Exception): pass
class NotFoundError(ApiError): pass
class EmptyRepoError(ApiError): pass
class TooBigError(ApiError): pass

