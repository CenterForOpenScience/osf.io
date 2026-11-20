from django.contrib.auth.models import Group

from tests.base import AdminTestCase
from admin.common_auth.forms import OBJECT_PERMISSION_GROUP_PREFIXES, UserRegistrationForm


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

    def test_group_choices_are_admin_app_groups_only(self):
        object_groups = {
            Group.objects.create(name=f'{prefix}test_group') for prefix in OBJECT_PERMISSION_GROUP_PREFIXES
        }
        choices = set(UserRegistrationForm().fields['group_perms'].queryset)

        assert {
            Group.objects.get(name=name)
            for name in ('read_only', 'osf_admin', 'metrics_only', 'celery_panel', 'admin_user_management')
        } <= choices
        assert not choices & object_groups

    def test_object_permission_groups_cannot_be_granted(self):
        for name in ('osfgroup_test_manager', 'institution_test_institutional_admins'):
            group = Group.objects.create(name=name)
            form = UserRegistrationForm({'osf_id': 'abc12', 'group_perms': [group.id]})
            assert not form.is_valid()
            assert 'group_perms' in form.errors
