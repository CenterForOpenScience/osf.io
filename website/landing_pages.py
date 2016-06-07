from flask import redirect

from framework.auth import cas
from framework.auth import decorators
from framework.auth import views as auth_views

from website.util import web_url_for


def connected_tools():
    return _landing_page(title='Connected Tools',
                         redirect_to=web_url_for('user_addons', _absolute=True))


def enriched_profile():
    return _landing_page(title='Enriched Profile',
                         redirect_to=web_url_for('profile_view', _absolute=True))


@decorators.must_be_logged_in
def _landing_page(auth, title, redirect_to, **kwargs):
        return redirect(redirect_to)
