import copy
import httplib as http
from framework.flask import request

class HTTPError(Exception):

    error_msgs = {
        http.BAD_REQUEST : {
            'message_short' : 'Bad request.',
            'message_long' : '',
        },
        http.UNAUTHORIZED : {
            'message_short' : 'Unauthorized.',
            'message_long' : 'You must log in to access this resource.',
        },
        http.FORBIDDEN : {
            'message_short' : 'Forbidden.',
            'message_long' : 'You do not have permission to perform this action.',
        },
        http.NOT_FOUND : {
            'message_short' : 'Page not found.',
            'message_long' : 'The requested resource could not be found.',
        },
        http.GONE : {
            'message_short' : 'Resource deleted.',
            'message_long' : 'The requested resource has been deleted.',
        },
    }

    def __init__(self, code, message=None, redirect_url=None, data=None):

        super(HTTPError, self).__init__(message)

        self.code = code
        self.redirect_url = redirect_url
        self.data = data or {}

        try:
            self.referrer = request.referrer
        except RuntimeError:
            self.referrer = None

    def to_data(self):

        data = copy.deepcopy(self.data)

        if self.code in self.error_msgs:
            data['message_short'] = self.error_msgs[self.code]['message_short']
            data['message_long'] = self.error_msgs[self.code]['message_long']
        else:
            data['message_short'] = data['message_long'] = 'Unknown error.'

        data['code'] = self.code
        data['referrer'] = self.referrer

        return data