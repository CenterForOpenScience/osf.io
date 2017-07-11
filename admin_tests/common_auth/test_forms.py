from tests.base import AdminTestCase
from admin.common_auth.forms import UserRegistrationForm


class TestUserRegistrationForm(AdminTestCase):
    def test_user_reg_form_success(self):
        form_data = {
            'osf_id': 'abc12',
        }
        form = UserRegistrationForm(form_data)
        self.assertTrue(form.is_valid())

    def test_user_reg_form_failure(self):
        # Every field is required, password length should be >= 5
        form_data = {
            'osf_id': 'thisiswaytoolong',
        }
        form = UserRegistrationForm(form_data)
        self.assertFalse(form.is_valid())
