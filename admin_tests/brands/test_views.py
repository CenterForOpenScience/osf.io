import pytest

from admin.brands import views

from django.test import RequestFactory
from django.core.exceptions import PermissionDenied

from osf.models import Brand
from django.contrib.auth.models import Permission
from osf_tests.factories import BrandFactory, AuthUserFactory

from admin_tests.utilities import setup_view

pytestmark = pytest.mark.django_db


@pytest.fixture()
def test_brand():
    return BrandFactory()

@pytest.fixture()
def test_brand_two():
    return BrandFactory()

@pytest.fixture()
def perm_user():
    user = AuthUserFactory()
    view_permission = Permission.objects.get(codename='view_brand')
    modify_permission = Permission.objects.get(codename='modify_brand')
    user.user_permissions.add(view_permission)
    user.user_permissions.add(modify_permission)
    user.save()
    return user

@pytest.fixture()
def perm_req(perm_user):
    req = RequestFactory().get('/fake_path')
    req.user = perm_user
    return req

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def req(user):
    req = RequestFactory().get('/fake_path')
    req.user = user
    return req


class TestBrandList:

    @pytest.fixture()
    def brand_list_view(self):
        return views.BrandList

    def test_get_queryset(self, test_brand, test_brand_two, brand_list_view):
        brands = list(brand_list_view().get_queryset())
        assert len(brands) == 2

    def test_failed_permissions(self, user, brand_list_view, req):
        with pytest.raises(PermissionDenied):
            brand_list_view.as_view()(req)

    def test_correct_view_permissions(self, perm_req, perm_user, brand_list_view):
        res = brand_list_view.as_view()(perm_req)
        assert res.status_code == 200


@pytest.mark.django_db
class TestBannerDisplay:

    @pytest.fixture()
    def brand_display_view(self):
        return views.BrandDisplay

    def test_get_object(self, brand_display_view, test_brand, req):
        view = brand_display_view()
        setup_view(view, req, brand_id=test_brand.id)
        obj = view.get_object()
        assert type(obj) is Brand
        assert obj.name == test_brand.name

    def test_context_data(self, perm_user, perm_req, brand_display_view, test_brand):
        view = brand_display_view()
        setup_view(view, req, brand_id=test_brand.id)
        data = view.get_context_data()
        assert data['brand']['name'] == test_brand.name

    def test_no_user_permissions_raises_error(self, req, brand_display_view, test_brand):
        with pytest.raises(PermissionDenied):
            brand_display_view.as_view()(req, brand_id=test_brand.id)

    def test_correct_view_permissions(self, perm_req, brand_display_view, test_brand):
        res = brand_display_view.as_view()(perm_req, brand_id=test_brand.id)
        assert res.status_code == 200


class TestCreateBrand:

    @pytest.fixture()
    def brand_create_view(self):
        return views.BrandCreate

    def test_no_user_permissions_raises_error(self, req, brand_create_view):
        with pytest.raises(PermissionDenied):
            brand_create_view.as_view()(req)

    def test_correct_view_permissions(self, perm_req, perm_user, brand_create_view):
        res = brand_create_view.as_view()(perm_req)
        assert res.status_code == 200
