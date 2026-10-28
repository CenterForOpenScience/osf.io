from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse


class AdminLoginRequiredMiddleware:
    """Require an active staff user for every admin view not marked with ``login_not_required``.
    Anonymous users are sent to the admin login page; signed-in users who aren't staff get a 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not getattr(view_func, 'login_required', True):
            return None
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('auth:login'))
        if not request.user.is_staff:
            raise PermissionDenied
        return None
