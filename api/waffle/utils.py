import waffle

from framework.auth.core import _get_current_user
from osf import features
from flask import request


class MockUser(object):
    is_authenticated = False


def flag_is_active(request, flag_name):
    """
    This function changes the typical flask request object so it can be used by django-waffle. Other modifications for
    django-waffle can be found in the __call__ method of OsfWebRenderer.
    :param flask request object:
    :return flask request object:
    """
    # Waffle does not enjoy NoneTypes as user values.
    request.user = _get_current_user() or MockUser()
    request.COOKIES = getattr(request, 'cookies', None)
    return waffle.flag_is_active(request, flag_name)


def storage_i18n_flag_active():
    return flag_is_active(request, features.STORAGE_I18N)


def storage_usage_flag_active():
    return flag_is_active(request, features.STORAGE_USAGE)
