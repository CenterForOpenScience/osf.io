from django.test import Client, TestCase
from tests.base import AdminTestCase
from admin.common_auth.models import MyUser
from django.core.urlresolvers import reverse
from admin.common_auth.forms import CustomUserRegistrationForm


class UserRegFormTestCase(AdminTestCase):
    def test_user_reg_form_success(self):
        form_data = {
            'email': 'example@example.com',
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2': 'password',
        }
        form = CustomUserRegistrationForm(form_data)
        self.assertTrue(form.is_valid())

    def test_user_reg_form_failure(self):
        # Every field is required, password length should be >= 5 (need Django 1.9 to use AUTH_PASSWORD_VALIDATORS)
        form_data = {
            'email': '',
            'first_name': '',
            'last_name': '',
            'password1': 'pass',
            'password2': 'pass',
        }
        form = CustomUserRegistrationForm(form_data)
        self.assertFalse(form.is_valid())


class UserRegSaveTestCase(AdminTestCase):
    def setUp(self):
        self.client = Client()
        user = MyUser.objects.create_user(email='zak@zak.com',
            password='secret')
        user.is_staff = True
        user.save()

    def test_registration_view_success(self):
        post_data = {
            'email': 'example@example.com',
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2': 'password',
        }

        self.client.login(email='zak@zak.com', password='secret')
        response = self.client.post(reverse('auth:register'), post_data)
        self.assertEqual(response.status_code, 302)

    def test_registration_view_failure(self):
        post_data = {
            'email': 'example@example.com',
            'first_name': '',
            'last_name': 'K',
            'password1': 'password',
            'password2': 'password',
        }

        self.client.login(email='zak@zak.com', password='secret')
        response = self.client.post(reverse('auth:register'), post_data)
        self.assertEqual(response.status_code, 400)
