from bitbucket3 import BitbucketError  # noqa


class ApiError(Exception):
    pass


class NotFoundError(ApiError):
    pass


class EmptyRepoError(ApiError):
    pass


class TooBigError(ApiError):
    pass
