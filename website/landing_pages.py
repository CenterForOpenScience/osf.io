from flask import redirect

from framework.auth import decorators

from website.util import web_url_for


@decorators.must_be_logged_in
def connected_tools(auth):
    return redirect(web_url_for('user_addons'))


@decorators.must_be_logged_in
def enriched_profile(auth):
    return redirect(web_url_for('profile_view'))
