class ApiError(Exception):
    pass


class NotFoundError(ApiError):
    pass


class EmptyRepoError(ApiError):
    pass


class TooBigError(ApiError):
    pass
