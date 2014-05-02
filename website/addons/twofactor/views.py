import httplib as http
import json

from framework import request
from framework.auth import get_current_user
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
        return {}

    raise HTTPError(403)