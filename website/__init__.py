# h/t https://gist.github.com/dufferzafar/b4f287d2de7d77d9a44c

from werkzeug.serving import WSGIRequestHandler
from werkzeug._internal import _log
from termcolor import colored
from colorama import init
init()

from website import settings

def log(self, type, message, *args):
    msg = '%s - - [%s] %s' % (self.address_string(),
                              self.log_date_time_string(),
                              message % args)
    # HTTP Status Code
    code = str(args[1])
    if code[0] == '2':  # 2xx - Success
        msg = colored(msg, 'green')
    elif code[0] == '1':  # 1xx - Informational
        msg = colored(msg, attrs=['bold'])
    elif code == '304':  # 304 - Resource Not Modified
        msg = colored(msg, color='blue', attrs=['bold'])
    elif code[0] == '3':  # 3xx - Redirection
        msg = colored(msg, color='blue')
    elif code == '404':  # 404 - Resource Not Found
        msg = colored(msg, color='yellow', attrs=['bold'])
    elif code[0] == '4':  # 4xx - Client Error
        msg = colored(msg, color='yellow', attrs=['bold'])
    else:  # 5xx, or any other response
        msg = colored(msg, color='red', attrs=['bold'])

    _log(type, msg)

if settings.DEV_MODE:
    WSGIRequestHandler.log = log
