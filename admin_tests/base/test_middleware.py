import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import resolve, reverse

from admin.base import settings as admin_settings
from admin.base.middleware import AdminLoginRequiredMiddleware
from admin.common_auth.views import LoginView
from admin_tests.utilities import all_admin_views, as_view_func, protected_views, public_views
from osf.models import AbstractNode, OSFUser
from osf_tests.factories import AuthUserFactory

pytestmark = pytest.mark.django_db

LOGIN_REDIRECT_PREFIX = f"{reverse('auth:login', urlconf='admin.base.urls')}?next="


def process_view(view_func, user):
    request = RequestFactory().get('/fake_path')
    request.user = user
    middleware = AdminLoginRequiredMiddleware(lambda r: None)
    return middleware.process_view(request, view_func, (), {})


def staff_user(**kwargs):
    user = AuthUserFactory(**kwargs)
    user.is_staff = True
    user.save()
    return user


@pytest.mark.urls('admin.base.urls')
class TestAdminLoginRequiredMiddleware:

    @pytest.mark.parametrize('view', protected_views())
    def test_anonymous_user_is_sent_to_login(self, view):
        response = process_view(as_view_func(view), AnonymousUser())
        assert response.status_code == 302
        assert response.url.startswith(LOGIN_REDIRECT_PREFIX)

    @pytest.mark.parametrize('view', protected_views())
    def test_non_staff_user_is_denied(self, view):
        with pytest.raises(PermissionDenied):
            process_view(as_view_func(view), OSFUser(is_active=True, is_staff=False))

    def test_staff_user_passes(self):
        assert process_view(resolve('/nodes/').func, staff_user()) is None

    def test_django_admin_site_requires_login(self):
        response = process_view(resolve('/admin/').func, AnonymousUser())
        assert response.status_code == 302
        assert response.url.startswith(LOGIN_REDIRECT_PREFIX)

    def test_login_is_public(self):
        assert process_view(as_view_func(LoginView), AnonymousUser()) is None

    def test_only_login_is_public(self):
        public = {view for view in all_admin_views() if not getattr(as_view_func(view), 'login_required', True)}
        assert public == public_views()


@pytest.mark.urls('admin.base.urls')
class TestAdminLoginRequiredMiddlewareEnabled:
    """
    Each request gets a different response from /nodes/ without AdminLoginRequiredMiddleware: the view itself
    returns 403 to anonymous users and lets in a non-staff user who holds osf.view_node.
    """

    @pytest.fixture(autouse=True)
    def admin_middleware(self, settings):
        settings.MIDDLEWARE = admin_settings.MIDDLEWARE

    def test_middleware_is_in_admin_settings(self):
        middleware = list(admin_settings.MIDDLEWARE)
        assert 'admin.base.middleware.AdminLoginRequiredMiddleware' in middleware

    def test_anonymous_request_is_redirected_to_login(self, client):
        response = client.get('/nodes/')
        assert response.status_code == 302
        assert response.url == f'{LOGIN_REDIRECT_PREFIX}/nodes/'

    def test_non_staff_request_is_denied(self, client):
        user = AuthUserFactory()
        user.user_permissions.add(Permission.objects.get(
            codename='view_node',
            content_type=ContentType.objects.get_for_model(AbstractNode),
        ))
        client.force_login(user)
        response = client.get('/nodes/')
        assert response.status_code == 403

    def test_anonymous_request_to_middleware_check_is_redirected_to_login(self, client):
        # /middleware_check/ route has no permission checks of its own
        # only AdminLoginRequiredMiddleware keeps it private
        response = client.get('/middleware_check/')
        assert response.status_code == 302
        assert response.url == f'{LOGIN_REDIRECT_PREFIX}/middleware_check/'
