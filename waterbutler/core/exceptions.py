import os
import http
import json
import asyncio


DEFAULT_ERROR_MSG = 'An error occurred while making a {response.method} request to {response.url}'


class AuthError(Exception):
    """The WaterButler related errors raised
    from a :class:`waterbutler.core.auth` should
    inherit from AuthError
    """

    def __init__(self, message, code=500, log_message=None):
        super().__init__(code)
        self.code = code
        self.log_message = log_message
        if isinstance(message, dict):
            self.data = message
            self.message = json.dumps(message)
        else:
            self.data = None
            self.message = message


class ProviderError(Exception):
    """The WaterButler related errors raised
    from a :class:`waterbutler.core.provider` should
    inherit from ProviderError
    """

    def __init__(self, message, code=400, log_message=None):
        super().__init__(code)
        self.code = code
        self.log_message = log_message
        if isinstance(message, dict):
            self.data = message
            self.message = json.dumps(message)
        else:
            self.data = None
            self.message = message

    def __repr__(self):
        return '<{}({}, {})>'.format(self.__class__.__name__, self.code, self.message)


class CopyError(ProviderError):
    pass

class CreateFolderError(ProviderError):
    pass

class DeleteError(ProviderError):
    pass


class DownloadError(ProviderError):
    pass


class IntraCopyError(ProviderError):
    pass


class IntraMoveError(ProviderError):
    pass


class MoveError(ProviderError):
    pass


class UploadError(ProviderError):
    pass


class MetadataError(ProviderError):
    pass


class RevisionsError(ProviderError):
    pass

class FolderNamingConflict(ProviderError):
    def __init__(self, path, name=None):
        super().__init__(
            'Cannot create folder "{name}" because a file or folder already exists at path "{path}"'.format(
                path=path,
                name=name or os.path.split(path.strip('/'))[1]
            ), code=409
        )


class NotFoundError(ProviderError):
    def __init__(self, path):
        super().__init__(
            'Could not retrieve file or directory {}'.format(path),
            code=http.client.NOT_FOUND,
        )

class InvalidPathError(ProviderError):
    def __init__(self, message):
        super().__init__(message, code=http.client.BAD_REQUEST)


@asyncio.coroutine
def exception_from_response(resp, error=ProviderError, **kwargs):
    """Build and return, not raise, an exception from a response object

    :param Response resp: An aiohttp.Response stream with a non 200 range status
    :param Exception error: The type of exception to be raised
    :param dict \*\*kwargs: Additional context to extract information from

    :rtype :class:`WaterButlerError`:
    """
    try:
        # Try to make an exception from our received json
        data = yield from resp.json()
        return error(data, code=resp.status)
    except Exception:
        pass

    try:
        data = yield from resp.read()
        return error({'response': data.decode('utf-8')}, code=resp.status)
    except TypeError:
        pass

    # When all else fails return the most generic return message
    return error(DEFAULT_ERROR_MSG.format(response=resp), code=resp.status)
