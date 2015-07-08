from flask import request

from framework.auth.decorators import must_be_logged_in

@must_be_logged_in
def prereg(auth, admin_type, *args, **kwargs):
    pass
