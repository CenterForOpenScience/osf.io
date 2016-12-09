class ApiError(Exception):
    pass

class NotFoundError(ApiError):
    pass

class GitLabError(Exception):
    pass
