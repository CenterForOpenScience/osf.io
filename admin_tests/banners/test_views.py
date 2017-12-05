import pytest

from admin.banners import views

from datetime import timedelta
from django.utils import timezone
from django.test import RequestFactory
from django.test.utils import override_settings

from osf.models import ScheduledBanner
from admin.banners.forms import BannerForm

from osf_tests.factories import ScheduledBannerFactory, AuthUserFactory

from admin_tests.utilities import setup_user_view, setup_form_view

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
        start_date=date + timedelta(days=1),
        end_date=date + timedelta(days=2)
    )

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def req():
    return RequestFactory().get('/fake_path')

class TestBannerList:

    @pytest.fixture()
    def view(self, req):
        view = views.BannerList()
        setup_user_view(view, req, user=user)
        return view

    def test_get_list(self, view, req):
        res = view.get(req)
        assert res.status_code == 200

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

class TestBannerDisplay:

    @pytest.fixture()
    def view(self, req, user, today_banner):
        view = views.BannerDisplay()
        setup_user_view(view, req, user=user)
        view.kwargs['banner_id'] = today_banner.id
        return view

    def test_get_object(self, view, today_banner):
        obj = view.get_object()
        assert type(obj) is ScheduledBanner
        assert obj.start_date == today_banner.start_date

    def test_context_data(self, view, today_banner):
        data = view.get_context_data()
        assert type(data) is dict
        assert type(data['banner']) is dict
        assert data['banner']['start_date'] == today_banner.start_date

    def test_get(self, view, req):
        res = view.get(req)
        assert res.status_code == 200

class TestChangeForm:
    #TODO: Add an actual test here
    @pytest.fixture()
    def view(self, req, user, tomorrow_banner):
        view = views.BannerChangeForm()
        setup_form_view(view, req, form=BannerForm())
        view.kwargs = {'banner_id': tomorrow_banner.id}
        return view

    def test_banner_form(self):
        new_data = {
            'color': '#000000',
            'default_text': 'sum txt',
            'start_date': '12/24/2017',
            'end_date': '12/25/2017',
            '_id': 'newbanner'
        }
        form = BannerForm(data=new_data)
        assert form.is_valid()

#TODO: I probably shouldnt need to do this
@override_settings(ROOT_URLCONF='admin.base.urls')
class TestDeleteBanner:
    @pytest.fixture
    def view(self, req, user, today_banner):
        view = views.DeleteBanner()
        setup_user_view(view, req, user=user)
        view.kwargs['banner_id'] = today_banner.id
        return view

    def test_delete(self, view, req, app):
        res = view.delete(req)
        assert res.url == '/banners/'
        assert res.status_code == 302

        #TODO: Test photo deletion

    def test_get(self, view, req):
        res = view.get(req)
        assert res.status_code == 200

class TestCreateBanner:
    @pytest.fixture
    def view(self, req):
        view = views.CreateBanner()
        setup_form_view(view, req, form=BannerForm())
        return view

    def test_get(self, view, req):
        res = view.get(req)
        assert res.status_code == 200
