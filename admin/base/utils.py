"""
Utility functions and classes
"""
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings


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
