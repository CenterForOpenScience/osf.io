import pytest

from admin.banners import views

from datetime import timedelta
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied


from osf.models import ScheduledBanner

from osf_tests.factories import ScheduledBannerFactory, AuthUserFactory

from admin_tests.utilities import setup_view

pytestmark = pytest.mark.django_db


@pytest.fixture
def date():
    return timezone.now()

@pytest.fixture()
def today_banner():
    return ScheduledBannerFactory()

@pytest.fixture()
def tomorrow_banner(date):
    return ScheduledBannerFactory(
        start_date=date + timedelta(days=1)
    )

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def req(user):
    req = RequestFactory().get('/fake_path')
    req.user = user
    return req


class TestBannerList:

    @pytest.fixture()
    def plain_view(self):
        return views.BannerList

    @pytest.fixture()
    def view(self, req, plain_view):
        view = plain_view()
        setup_view(view, req)
        return view

    def test_get_queryset(self, view, today_banner, tomorrow_banner):
        banners = list(view.get_queryset())
        assert len(banners) == 2
        assert today_banner in banners
        assert tomorrow_banner in banners

    def test_context_data(self, view, today_banner, tomorrow_banner):
        view.object_list = view.get_queryset()
        data = view.get_context_data()
        assert type(data) is dict
        assert (len(data['banners']), 2)
        assert type(data['banners'][0]) is ScheduledBanner

    def test_no_user_permissions_raises_error(self, req, plain_view):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req)

    def test_correct_view_permissions(self, req, user, plain_view):
        view_permission = Permission.objects.get(codename='view_scheduledbanner')
        user.user_permissions.add(view_permission)
        user.save()

        res = plain_view.as_view()(req)
        assert res.status_code == 200


@pytest.mark.urls('admin.base.urls')
class TestBannerDisplay:

    @pytest.fixture()
    def plain_view(self):
        return views.BannerDisplay

    @pytest.fixture()
    def view(self, req, plain_view, today_banner):
        view = plain_view()
        setup_view(view, req, banner_id=today_banner.id)
        return view

    def test_get_object(self, view, today_banner):
        obj = view.get_object()
        assert type(obj) is ScheduledBanner
        assert obj.name == today_banner.name

    def test_context_data(self, view, today_banner):
        data = view.get_context_data()
        assert type(data) is dict
        assert type(data['banner']) is dict
        assert data['banner']['name'] == today_banner.name

    def test_no_user_permissions_raises_error(self, req, plain_view, today_banner):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req, banner_id=today_banner.id)

    def test_correct_view_permissions(self, req, user, plain_view, today_banner):
        view_permission = Permission.objects.get(codename='view_scheduledbanner')
        user.user_permissions.add(view_permission)
        user.save()

        res = plain_view.as_view()(req, banner_id=today_banner.id)
        assert res.status_code == 200


@pytest.mark.urls('admin.base.urls')
class TestDeleteBanner:

    @pytest.fixture()
    def plain_view(self):
        return views.DeleteBanner

    @pytest.fixture()
    def view(self, req, plain_view, today_banner):
        view = plain_view()
        setup_view(view, req, banner_id=today_banner.id)
        return view

    def test_delete(self, view, req):
        res = view.delete(req)
        assert res.url == '/banners/'
        assert res.status_code == 302

    def test_no_user_permissions_raises_error(self, req, plain_view, today_banner):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req, banner_id=today_banner.id)

    def test_correct_permissions(self, req, user, plain_view, today_banner):
        delete_permission = Permission.objects.get(codename='delete_scheduledbanner')
        user.user_permissions.add(delete_permission)
        user.save()

        res = plain_view.as_view()(req, banner_id=today_banner.id)
        assert res.status_code == 200

class TestCreateBanner:

    @pytest.fixture()
    def plain_view(self):
        return views.CreateBanner

    def test_no_user_permissions_raises_error(self, req, plain_view):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req)

    def test_correct_view_permissions(self, req, user, plain_view):
        change_permission = Permission.objects.get(codename='change_scheduledbanner')
        user.user_permissions.add(change_permission)
        user.save()

        res = plain_view.as_view()(req)
        assert res.status_code == 200
