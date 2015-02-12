import json

DMCA_ERROR = '''
<div class="alert alert-info" role="alert">
This file has been the subject of a DMCA take down
and is unable to be rendered by the Open Science Framework
</div>'''


STATUS_CODE_ERROR_MAP = {
    461: DMCA_ERROR
}


class RenderFailureException(Exception):
    def __init__(self, http_status_code, **additional):
        additional['status_code'] = http_status_code

        msg = json.dumps(additional)
        super(Exception, self).__init__(msg)


def error_message_or_exception(http_status_code, **info):
    err = STATUS_CODE_ERROR_MAP.get(http_status_code)

    if not err:
        raise RenderFailureException(http_status_code)

    return err.format(**info)
