from framework.exceptions import HTTPError
import httplib as http

def api_call(func):
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except self.api_error_classes as e:
            raise HTTPError(http.BAD_GATEWAY, message=e.message)
    return wrapper