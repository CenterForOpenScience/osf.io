"""
Utility functions and classes
"""
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.http import urlencode


class OSFAdmin(UserPassesTestMixin):
    login_url = settings.LOGIN_URL
    permission_denied_message = 'You are not in the OSF admin group.'

    def handle_no_permission(self):
        if not self.request.user.is_authenticated():
            return redirect_to_login(self.request.get_full_path(),
                                     self.get_login_url(),
                                     self.get_redirect_field_name())
        else:
            raise PermissionDenied(self.get_permission_denied_message())

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.is_in_group('osf_admin')


class SuperUser(OSFAdmin):
    permission_denied_message = (
        'You are not a superuser,'
        ' please contact one in order to do this action.'
    )

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.is_superuser


class PreregAdmin(OSFAdmin):
    """For testing for Prereg credentials of user."""
    permission_denied_message = 'You are not in the Pre-reg admin group.'

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.is_in_group('prereg_group')


def reverse_qs(view, urlconf=None, args=None, kwargs=None, current_app=None, query_kwargs=None):
    base_url = reverse(view, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)
    if query_kwargs:
        return '{}?{}'.format(base_url, urlencode(query_kwargs))
