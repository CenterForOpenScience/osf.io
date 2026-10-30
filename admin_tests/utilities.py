"""
Utilities to help run Django tests
* setup_view - replaces as_view
"""
from django.urls import URLPattern, URLResolver, get_resolver

from admin.common_auth.views import LoginView
from osf_tests.factories import UserFactory


def setup_view(view, request, *args, **kwargs):
    """Mimic as_view() returned callable, but returns view instance

    http://tech.novapost.fr/django-unit-test-your-views-en.html
    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view


def setup_form_view(view, request, form, *args, **kwargs):
    """Mimic as_view and with forms to skip some of the context"""
    view.request = request
    try:
        view.request.user = request.user
    except AttributeError:
        view.request.user = UserFactory()
    view.args = args
    view.kwargs = kwargs
    view.form = form
    return view


def setup_user_view(view, request, user, *args, **kwargs):
    view.request = request
    view.request.user = user
    view.args = args
    view.kwargs = kwargs
    return view


def setup_log_view(view, request, *args, **kwargs):
    view.request = request
    try:
        view.request.user = request.user
    except AttributeError:
        view.request.user = UserFactory()
    view.args = args
    view.kwargs = kwargs
    return view


def handle_post_view_request(request, view, obj, guid):
    view = setup_view(view, request, guid=guid)
    view.post(request)
    obj.refresh_from_db()
    return obj


def get_all_views(url_patterns, views=None, module=None):
    if views is None:
        views = set()
    for pattern in url_patterns:
        if isinstance(pattern, URLResolver):
            get_all_views(pattern.url_patterns, views, module=module)
        elif isinstance(pattern, URLPattern):
            # Handle function-based and class-based views
            view = pattern.callback
            if hasattr(view, 'view_class'):
                view = view.view_class
            if module and not view.__module__.startswith(f'{module}.'):
                continue
            views.add(view)
    return views


def as_view_func(view):
    return view.as_view() if isinstance(view, type) else view


def all_admin_views():
    return get_all_views(get_resolver('admin.base.urls').url_patterns, module='admin')


def public_views():
    return {LoginView}


def protected_views():
    # Sorted so every xdist worker collects the same tests in the same order
    return sorted(all_admin_views() - public_views(), key=lambda view: (view.__name__, view.__module__))
