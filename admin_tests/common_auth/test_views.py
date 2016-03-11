from django.test import Client, TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import User, Group
from models import MyUser
from django.core.urlresolvers import reverse
from forms import CustomUserRegistrationForm
from views import register


class UserRegFormTestCase(TestCase):
    def test_user_reg_form_success(self):
        group_perms = Group.objects.all()
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

class UserRegSaveTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        user = MyUser.objects.create_user(email='zak@zak.com',
            password='secret')
        user.is_staff = True
        user.save()


    def test_registration_view_success(self):
        group_perms = Group.objects.filter(name="prereg_group")

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
