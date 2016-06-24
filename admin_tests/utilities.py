"""
Utilities to help run Django tests
* setup_view - replaces as_view
"""
from admin_tests.factories import UserFactory


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
