from nose import tools as nt
import mock

from django.test import RequestFactory
from tests.base import AdminTestCase
from tests.factories import AuthUserFactory

from admin_tests.utilities import setup_form_view

from admin.common_auth.models import MyUser
from admin.common_auth.views import RegisterUser
from admin.common_auth.forms import UserRegistrationForm


class TestRegisterUser(AdminTestCase):
    def setUp(self):
        super(TestRegisterUser, self).setUp()
        self.user = AuthUserFactory()
        self.data = {
            'email': self.user.email,
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2': 'password',
            'osf_id': 'abc12',
        }
        self.view = RegisterUser()
        self.request = RequestFactory().post('fake_path')

    def test_osf_id_invalid(self):
        form = UserRegistrationForm(data=self.data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.view, self.request, form)
        res = view.form_valid(form)
        nt.assert_equal(res.status_code, 404)
        nt.assert_in('OSF user with id', res.content)

    @mock.patch('admin.common_auth.views.PasswordResetForm.save')
    @mock.patch('admin.common_auth.views.messages.success')
    def test_add_user(self, mock_save, mock_message):
        count = MyUser.objects.count()
        self.data.update(osf_id=self.user._id)
        form = UserRegistrationForm(data=self.data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.view, self.request, form)
        view.form_valid(form)
        nt.assert_true(mock_save.called)
        nt.assert_true(mock_message.called)
        nt.assert_equal(MyUser.objects.count(), count + 1)
