from flask import redirect

from framework.auth import views as auth_views
from framework.auth.decorators import collect_auth


def connected_tools():
    return _landing_page(title='Connected Tools',
                         content_path='/public/pages/help/addons.mako',
                         redirect_to='/settings/addons/')


def enriched_profile():
    return _landing_page(title='Enriched Profile',
                         content_path='/public/pages/help/user_profile.mako',
                         redirect_to='/profile/',)


@collect_auth
def _landing_page(auth, title, content_path, redirect_to, **kwargs):
    if auth.logged_in:
        return redirect(kwargs.get('redirect_to', redirect_to))
    data = auth_views.auth_login(**kwargs)
    try:
        data[0]['title_text'] = title
        data[0]['content_template_path'] = content_path
        data[0]['next_url'] = redirect_to
    except TypeError:
        pass

    return data
