"""
Utility functions and classes
"""
from django.core.urlresolvers import reverse
from django.utils.http import urlencode


def reverse_qs(view, urlconf=None, args=None, kwargs=None, current_app=None, query_kwargs=None):
    base_url = reverse(view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    if query_kwargs:
        return '{}?{}'.format(base_url, urlencode(query_kwargs))


def osf_staff_check(user):
    return user.is_authenticated() and user.is_staff
