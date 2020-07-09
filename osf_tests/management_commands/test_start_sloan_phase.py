import pytest

from django.core.management import call_command

from osf_tests.factories import (
    AuthUserFactory
)
from waffle.models import (
    Switch,
    Flag
)

@pytest.mark.django_db
class TestStartSloanPhase:

    @pytest.fixture()
    def user(self):
        user = AuthUserFactory()
        user.add_system_tag('no_waffle:sloan|coi')
        user.add_system_tag('no_waffle:sloan|data')
        user.add_system_tag('no_waffle:sloan|prereg')
        user.save()
        return user

    @pytest.mark.parametrize('feature', ['coi', 'data', 'prereg'])
    def test_start_phase(self, user, feature):
        call_command('start_sloan_phase', f'--flag={feature}')

        flag = Flag.objects.get(name=f'sloan_{feature}_display')
        assert flag.everyone is None
        assert flag.percent == 50

        switch = Switch.objects.get(name=f'sloan_{feature}_input')
        assert switch.active
        assert f'no_waffle:sloan|{feature}' not in user.all_tags
        assert f'waffle:sloan|{feature}' not in user.all_tags

    def test_start_phase_invalid(self, user):
        with pytest.raises(AssertionError) as e:
            call_command('start_sloan_phase', '--flag=notright')

        assert str(e.value) == 'the given flag : \'notright\' was invalid'
