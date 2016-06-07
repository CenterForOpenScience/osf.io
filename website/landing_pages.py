from flask import redirect

from framework.auth import cas
from framework.auth import decorators
from framework.auth import views as auth_views

from website.util import web_url_for


def connected_tools():
    return _landing_page(title='Connected Tools',
                         content_path='/public/pages/help/addons.mako',
                         redirect_to=web_url_for('user_addons', _absolute=True))


def enriched_profile():
    return _landing_page(title='Enriched Profile',
                         content_path='/public/pages/help/user_profile.mako',
                         redirect_to=web_url_for('profile_view', _absolute=True))


@decorators.collect_auth
def _landing_page(auth, title, content_path, redirect_to, **kwargs):
    if auth.logged_in:
        return redirect(kwargs.get('redirect_to', redirect_to))
    data = auth_views.auth_login(**kwargs)
    try:
        data[0]['title_text'] = title
        data[0]['content_template_path'] = content_path
        # TODO: ask Steve on what is landing_page
        data[0]['login_url'] = cas.get_login_url(redirect_to)
    except TypeError:
        pass

    return data
