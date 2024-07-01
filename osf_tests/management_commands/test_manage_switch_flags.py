import pytest
from unittest.mock import patch, mock_open

from waffle.models import Flag, Switch
from osf.management.commands.manage_switch_flags import manage_waffle

@pytest.mark.django_db
class TestWaffleFlags():

    @pytest.fixture()
    def yaml_data(self):
        return '''
            flags:
              - flag_name: TEST_FLAG
                name: test_flag_page
                note: This is for tests only
                everyone: true
            switches:
              - flag_name: TEST_SWITCH
                name: test_switch_page
                note: This is for tests only
                active: false
        '''

    def test_manage_flags(self, yaml_data):
        with patch('builtins.open', mock_open(read_data=yaml_data)):
            manage_waffle()
        assert Flag.objects.all().count() == 1
        assert Switch.objects.all().count() == 1

    def test_manage_flags_delete(self, yaml_data):
        Flag.objects.create(name='new_test_flag')
        Switch.objects.create(name='new_test_flag')

        with patch('builtins.open', mock_open(read_data=yaml_data)):
            manage_waffle()
        manage_waffle(delete_waffle=True)
        assert not Flag.objects.filter(name='new_test_flag')
        assert not Switch.objects.filter(name='new_test_switch')
