from flask import request

from framework.auth.decorators import must_be_logged_in

from website.admin import PREREG
from website.admin.decorators import must_be_super_on

@must_be_logged_in
#@must_be_super_on(PREREG)
def prereg(auth, *args, **kwargs):
    user = auth.user
    return {'id': user._id}
