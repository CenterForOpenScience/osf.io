class ApiError(Exception):
    pass

class NotFoundError(ApiError):
    pass

class AuthError(ApiError):
    pass

class GitLabError(Exception):
    pass
