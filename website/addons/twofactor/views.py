# -*- coding: utf-8 -*-
import httplib as http

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.project.decorators import must_have_addon


@must_be_logged_in
@must_have_addon('twofactor', 'user')
def user_settings(user_addon, *args, **kwargs):

    code = request.json.get('code')
    if code is None:
        raise HTTPError(code=http.BAD_REQUEST)

    if user_addon.verify_code(code):
        user_addon.is_confirmed = True
        user_addon.save()
        return {'message': 'Successfully verified two-factor authentication.'}, http.OK
    raise HTTPError(http.FORBIDDEN, data=dict(
        message_short='Forbidden',
        message_long='The two-factor verification code you provided is invalid.'
    ))
