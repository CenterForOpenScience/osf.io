from unittest import mock
import pytest

from django.test import RequestFactory
from django.http import Http404
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory

from admin_tests.utilities import setup_form_view

from osf.models.user import OSFUser
from admin.common_auth.views import RegisterUser
from admin.common_auth.forms import UserRegistrationForm


class TestRegisterUser(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.data = {
            'osf_id': 'abc12',
        }
        self.view = RegisterUser()
        self.request = RequestFactory().post('fake_path')

    def test_osf_id_invalid(self):
        form = UserRegistrationForm(data=self.data)
        assert form.is_valid()
        view = setup_form_view(self.view, self.request, form)
        with pytest.raises(Http404):
            view.form_valid(form)

    @mock.patch('admin.common_auth.views.messages.success')
    def test_add_user(self, mock_save):
        count = OSFUser.objects.count()
        self.data.update(osf_id=self.user._id)
        form = UserRegistrationForm(data=self.data)
        assert form.is_valid()
        view = setup_form_view(self.view, self.request, form)
        view.form_valid(form)
        assert mock_save.called
        assert OSFUser.objects.count() == count + 1
