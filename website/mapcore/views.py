# -*- coding: utf-8 -*-

import logging

from framework.auth.decorators import must_be_logged_in_without_checking_mapcore_token
from framework.flask import redirect  # VOL-aware redirect
from flask import request

# mapcore library
from nii.mapcore import mapcore_request_authcode, mapcore_receive_authcode

logger = logging.getLogger(__name__)

@must_be_logged_in_without_checking_mapcore_token
def mapcore_oauth_start(auth):
    return {'mapcore_authcode_url': mapcore_request_authcode(
        auth.user, request.args.to_dict())
    }

@must_be_logged_in_without_checking_mapcore_token
def mapcore_oauth_complete(auth):
    return redirect(mapcore_receive_authcode(
        auth.user, request.args.to_dict()))
