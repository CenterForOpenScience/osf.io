import json

DMCA_ERROR = '''
<div class="alert alert-info" role="alert">
This file has been the subject of a DMCA take down
and is unable to be rendered by the Open Science Framework
</div>
<style>.file-download{{display: none;}}</style>
'''
# Note: the style is for disabling download buttons


STATUS_CODE_ERROR_MAP = {
    461: DMCA_ERROR
}


class RenderFailureException(Exception):
    '''An exception for temporary errors when attempting to render a file
    IE 500s 400s etc etc
    '''
    def __init__(self, http_status_code, **additional):
        additional['status_code'] = http_status_code

        msg = json.dumps(additional)
        super(RenderFailureException, self).__init__(msg)


class RenderNotPossibleException(Exception):
    '''An exception indicating an an avoidable render error
    that should therefore be cached. IE dropbox's DMCA take downs
    '''
    def __init__(self, msg):
        self.renderable_error = msg
        super(RenderNotPossibleException, self).__init__(msg)


def error_message_or_exception(http_status_code, **info):
    err = STATUS_CODE_ERROR_MAP.get(http_status_code)

    if not err:
        raise RenderFailureException(http_status_code)

    raise RenderNotPossibleException(err.format(**info))
