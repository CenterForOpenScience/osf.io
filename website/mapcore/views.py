# -*- coding: utf-8 -*-

import logging

from framework.auth.core import _get_current_user
from framework.auth.decorators import must_be_logged_in_without_checking_mapcore_token
from framework.flask import redirect  # VOL-aware redirect
from flask import request
from website.ember_osf_web.decorators import MockUser

# mapcore library
from nii.mapcore import mapcore_request_authcode, mapcore_receive_authcode

logger = logging.getLogger(__name__)

# mAP core
@must_be_logged_in_without_checking_mapcore_token
def mapcore_oauth_start(**kwargs):
    # for debug
    # enterance for OAuth
    return redirect(mapcore_request_authcode(request=request.args.to_dict()))

@must_be_logged_in_without_checking_mapcore_token
def mapcore_oauth_complete(**kwargs):
    return redirect(mapcore_receive_authcode(_get_current_user() or MockUser(), request.args.to_dict()))
