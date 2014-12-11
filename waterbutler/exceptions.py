import json
import asyncio

from tornado.web import HTTPError


DEFAULT_ERROR_MSG = 'An error occurred while making a {response.method} request to {response.url}'


class WaterButlerError(HTTPError):
    def __init__(self, message, code=500, log_message=None):
        if isinstance(message, dict):
            self.data = message
            message = json.dumps(message)
        else:
            self.data = None
        super().__init__(code, log_message=log_message, reason=message)


class ProviderError(WaterButlerError):
    def __init__(self, message, code=400, log_message=None):
        super().__init__(message, code=code, log_message=log_message)


class FileNotFoundError(ProviderError):
    def __init__(self, path):
        super().__init__('Could not retrieve file or directory {0}'.format(path), code=404)


# A dict of status codes mapped to
# an exeption and a tuple of args to extract from kwargs
CODE_TO_ERROR = {
    404: (FileNotFoundError, ('path',))  # Sha?
}


@asyncio.coroutine
def exception_from_reponse(resp, **kwargs):
    """Build and return, not raise, an exception from a response
    :param Response resp: An AioResponse obj with a non 200 range status
    :param dict **kwargs: Additional context to extract information from
    :rtype WaterButlerError:
    """
    try:
        # If our exception exists build and return it
        exc, args = CODE_TO_ERROR[resp.status]
        return exc(**{
            key: val
            for key, val
            in kwargs.items()
            if key in args
        })
    except KeyError:
        try:
            # Try to make an exception from our recieved json
            data = yield from resp.json()
            return WaterButlerError(data, code=resp.status)
        except Exception:
            # When all else fails return the most generic return message
            return WaterButlerError(DEFAULT_ERROR_MSG.format(response=resp), code=resp.status)
