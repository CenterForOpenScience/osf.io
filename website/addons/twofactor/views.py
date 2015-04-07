# -*- coding: utf-8 -*-
import httplib as http

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.project.decorators import must_have_addon


@must_be_logged_in
@must_have_addon('twofactor', 'user')
def user_settings_put(user_addon, *args, **kwargs):

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

@must_be_logged_in
def user_settings_get(auth, *args, **kwargs):

    user_addon = auth.user.get_addon('twofactor')
    result = {}
    if user_addon:
        result = user_addon.to_json(auth.user)
    else:
        result = {
            'is_enabled': False,
            'is_confirmed': False,
            'secret': None,
            'drift': None,
        }
    return {
        'result': result
    }


@must_be_logged_in
def enable_twofactor(auth, *args, **kwargs):

    user_addon = auth.user.get_addon('twofactor')
    if user_addon:
        return HTTPError(http.BAD_REQUEST, message='This user already has twofactor enabled')

    user_addon = auth.user.get_or_add_addon('twofactor', auth=auth)
    auth.user.save()
    return user_addon.to_json(auth.user)
