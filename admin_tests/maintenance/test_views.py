import pytest

from admin.maintenance import views

from django.utils import timezone
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

import website.maintenance as maintenance
from osf.models import MaintenanceState
from osf_tests.factories import AuthUserFactory

from admin_tests.utilities import setup_view

pytestmark = pytest.mark.django_db


@pytest.fixture
def date():
    return timezone.now()

@pytest.fixture()
def maintenance_alert():
    maintenance.set_maintenance('')
    return maintenance.get_maintenance()

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def req(user):
    req = RequestFactory().get('/fake_path')
    req.user = user
    return req

@pytest.mark.urls('admin.base.urls')
class TestMaintenanceDisplay:

    @pytest.fixture()
    def plain_view(self):
        return views.MaintenanceDisplay

    @pytest.fixture()
    def view(self, req, plain_view):
        view = plain_view()
        setup_view(view, req)
        return view

    def test_has_alert(self, view, maintenance_alert):
        data = view.get_context_data()
        assert data['current_alert']

    def test_has_no_alert(self, view):
        data = view.get_context_data()
        assert not data.get('current_alert')

    def test_no_user_permissions_raises_error(self, req, plain_view):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req)

    def test_correct_view_permissions(self, req, user, plain_view):
        view_permission = Permission.objects.get(codename='change_maintenancestate')
        user.user_permissions.add(view_permission)
        user.save()

        res = plain_view.as_view()(req)
        assert res.status_code == 200

    def test_create_maintenance(self, view, req):
        message = 'Whooo. Its Custom!'
        req.POST = {'start': '2018/01/27 10:24', 'level': 1, 'message': message}
        view.post(req)
        assert MaintenanceState.objects.first().message == message


@pytest.mark.urls('admin.base.urls')
class TestDeleteMaintenance:

    @pytest.fixture()
    def plain_view(self):
        return views.DeleteMaintenance

    @pytest.fixture()
    def view(self, req, plain_view):
        view = plain_view()
        setup_view(view, req)
        return view

    def test_delete(self, view, req):
        res = view.delete(req)
        assert res.url == '/maintenance/'
        assert res.status_code == 302
        assert MaintenanceState.objects.all().count() == 0

    def test_no_user_permissions_raises_error(self, req, plain_view):
        with pytest.raises(PermissionDenied):
            plain_view.as_view()(req)

    def test_correct_view_permissions(self, req, user, plain_view):
        view_permission = Permission.objects.get(codename='delete_maintenancestate')
        user.user_permissions.add(view_permission)
        user.save()

        res = plain_view.as_view()(req)
        assert res.status_code == 200
