from tests.base import AdminTestCase
from admin.common_auth.forms import UserRegistrationForm


class TestUserRegistrationForm(AdminTestCase):
    def test_user_reg_form_success(self):
        form_data = {
            'email': 'example@example.com',
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2': 'password',
            'osf_id': 'abc12',
        }
        form = UserRegistrationForm(form_data)
        self.assertTrue(form.is_valid())

    def test_user_reg_form_failure(self):
        # Every field is required, password length should be >= 5
        form_data = {
            'email': '',
            'first_name': '',
            'last_name': '',
            'password1': 'pass',
            'password2': 'pass',
        }
        form = UserRegistrationForm(form_data)
        self.assertFalse(form.is_valid())
