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
def _landing_page(*args, **kwargs):
    if kwargs['auth'].logged_in:
        return redirect(kwargs.get('redirect_to', '/'))
    data = auth_views.auth_login(*args, **kwargs)
    try:
        data[0]['title_text'] = kwargs.get('title')
        data[0]['content_template_path'] = kwargs.get('content_path')
        data[0]['next_url'] = kwargs.get("redirect_to")
    except TypeError:
        pass

    return data