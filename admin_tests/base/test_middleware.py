import pytest
from django.contrib.auth.models import AnonymousUser, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.urls import URLPattern, URLResolver, get_resolver, resolve, reverse

from admin.base import settings as admin_settings
from admin.base.middleware import AdminLoginRequiredMiddleware
from admin.common_auth.views import LoginView
from osf.models import AbstractNode, OSFUser
from osf_tests.factories import AuthUserFactory

pytestmark = pytest.mark.django_db


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


ALL_ADMIN_VIEWS = get_all_views(get_resolver('admin.base.urls').url_patterns, module='admin')
PUBLIC_VIEWS = {LoginView}
# Sorted so every xdist worker collects the same tests in the same order
PROTECTED_VIEWS = sorted(ALL_ADMIN_VIEWS - PUBLIC_VIEWS, key=lambda view: (view.__name__, view.__module__))
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

    @pytest.mark.parametrize('view', PROTECTED_VIEWS)
    def test_anonymous_user_is_sent_to_login(self, view):
        response = process_view(as_view_func(view), AnonymousUser())
        assert response.status_code == 302
        assert response.url.startswith(LOGIN_REDIRECT_PREFIX)

    @pytest.mark.parametrize('view', PROTECTED_VIEWS)
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
        public = {view for view in ALL_ADMIN_VIEWS if not getattr(as_view_func(view), 'login_required', True)}
        assert public == PUBLIC_VIEWS


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
