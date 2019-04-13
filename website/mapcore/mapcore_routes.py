# -*- coding: utf-8 -*-

import logging

from framework.auth.core import _get_current_user
from framework.flask import redirect  # VOL-aware redirect
from flask import request, send_from_directory, Response, stream_with_context
from website.ember_osf_web.decorators import ember_flag_is_active, MockUser, storage_i18n_flag_active

# mapcore library
from nii.mapcore import mapcore_request_authcode
from nii.mapcore import mapcore_receive_authcode

logger = logging.getLogger(__name__)

# mAP core
def mapcore_oauth_start(**kwargs):
    # enterance for OAuth
    return redirect(mapcore_request_authcode(request=request.args.to_dict()))

def mapcore_oauth_complete(**kwargs):
    # Redirect to COS News page
    logger.info('Enter oauth_finish()')
    return redirect(mapcore_receive_authcode(_get_current_user() or MockUser(), request.args.to_dict()))
