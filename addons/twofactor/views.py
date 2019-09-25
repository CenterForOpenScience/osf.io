# -*- coding: utf-8 -*-
from rest_framework import status as http_status

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError

from website.project.decorators import must_have_addon

from addons.twofactor.utils import serialize_settings

@must_be_logged_in
@must_have_addon('twofactor', 'user')
def twofactor_settings_put(user_addon, *args, **kwargs):

    code = request.json.get('code')
    if code is None:
        raise HTTPError(code=http_status.HTTP_400_BAD_REQUEST)

    if user_addon.verify_code(code):
        user_addon.is_confirmed = True
        user_addon.save()
        return {'message': 'Successfully verified two-factor authentication.'}, http_status.HTTP_200_OK
    raise HTTPError(http_status.HTTP_403_FORBIDDEN, data=dict(
        message_short='Forbidden',
        message_long='The two-factor verification code you provided is invalid.'
    ))

@must_be_logged_in
def twofactor_settings_get(auth, *args, **kwargs):
    return {
        'result': serialize_settings(auth),
    }


@must_be_logged_in
def twofactor_enable(auth, *args, **kwargs):
    user = auth.user

    if user.has_addon('twofactor'):
        return HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(message_long='This user already has two-factor enabled'))

    user.add_addon('twofactor', auth=auth)
    user_addon = user.get_addon('twofactor')
    user_addon.save()
    user.save()
    return {
        'result': serialize_settings(auth),
    }

@must_be_logged_in
@must_have_addon('twofactor', 'user')
def twofactor_disable(auth, *args, **kwargs):

    if auth.user.delete_addon('twofactor', auth=auth):
        auth.user.save()
        return {}
    else:
        raise HTTPError(http_status.HTTP_500_INTERNAL_SERVER_ERROR, data=dict(
            message_long='Could not disable two-factor at this time'
        ))
