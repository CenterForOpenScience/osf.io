from django.test import Client, TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from forms import CustomUserRegistrationForm
from common_auth.views import register


class UserRegFormTestCase(TestCase):
    def test_user_reg_form_success(self):
        group_perms = Group.objects.filter(name="prereg_group")
        form_data = {
            'email': 'example@example.com',
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2', 'password',
            'group_perms': group_perms,
        }
        form = CustomUserRegistrationForm(form_data)
        self.assertTrue(form.is_valid())


    def test_user_reg_form_failure(self):
        # Every field is required, password length should be >= 5
        form_data = {
            'email': '',
            'first_name': '',
            'last_name': '',
            'password1': 'pass',
            'password2', 'pass',
            'group_perms': '',
        }
        form = CustomUserRegistrationForm(form_data)
        self.assertFalse(form.is_valid())

class UserRegSaveTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='Zak', email='zak@zak.com',
            password='secret', is_staff=True)

    def test_registration(self):
        request.user = self.user
        request = self.factory.post('/register')
        group_perms = Group.objects.filter(name="prereg_group")

        post_data = {
            'email': 'example@example.com',
            'first_name': 'Zak',
            'last_name': 'K',
            'password1': 'password',
            'password2', 'password',
            'group_perms': group_perms,
        }

        response = self.client.post('/register', post_data)
        self.assertEqual(response.status_code, 200)


