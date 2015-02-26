import http
import json
import asyncio


DEFAULT_ERROR_MSG = 'An error occurred while making a {response.method} request to {response.url}'


class ProviderError(Exception):

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


class CopyError(ProviderError):
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


class NotFoundError(ProviderError):
    def __init__(self, path):
        super().__init__(
            'Could not retrieve file or directory {}'.format(path),
            code=http.client.NOT_FOUND,
        )


@asyncio.coroutine
def exception_from_response(resp, error=ProviderError, **kwargs):
    """Build and return, not raise, an exception from a response
    :param Response resp: An AioResponse stream with a non 200 range status
    :param dict **kwargs: Additional context to extract information from
    :rtype WaterButlerError:
    """
    try:
        # Try to make an exception from our received json
        data = yield from resp.json()
        return error(data, code=resp.status)
    except Exception:
        # When all else fails return the most generic return message
        return error(DEFAULT_ERROR_MSG.format(response=resp), code=resp.status)
