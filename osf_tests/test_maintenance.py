import unittest
from datetime import timedelta

import pytest
from django.utils import timezone

from website import maintenance
from osf.models import MaintenanceState


pytestmark = pytest.mark.django_db


class TestMaintenance(unittest.TestCase):

    def tearDown(self):
        MaintenanceState.objects.all().delete()

    def test_set_maintenance_with_start_date(self):
        start = timezone.now()
        maintenance.set_maintenance(_id='test', message='', start=start.isoformat())
        current_state = MaintenanceState.objects.get(_id='test')

        assert current_state.start == start
        assert current_state.end == start + timedelta(1)

    def test_set_maintenance_with_end_date(self):
        end = timezone.now()
        maintenance.set_maintenance(_id='test', message='', end=end.isoformat())
        current_state = MaintenanceState.objects.get(_id='test')

        assert current_state.start == end - timedelta(1)
        assert current_state.end == end

    def test_set_maintenance_in_future(self):
        start = (timezone.now() + timedelta(1))
        maintenance.set_maintenance(_id='test', message='', start=start.isoformat())
        current_state = MaintenanceState.objects.get(_id='test')

        assert current_state.start == start
        assert current_state.end == start + timedelta(1)

    def test_set_maintenance_level(self):
        maintenance.set_maintenance(_id='test', message='')
        maintenance.set_maintenance(_id='test2', message='', level=3)

        assert MaintenanceState.objects.get(_id='test').level == 1
        assert MaintenanceState.objects.get(_id='test2').level == 3

    def test_get_maintenance_states(self):
        maintenance.set_maintenance(_id='test', message='testing', level=2)
        maintenance.set_maintenance(_id='danger test', message='apocalypse testing', level=3)

        maintenance_states = maintenance.get_maintenance_states()

        assert maintenance_states[0]['_id'] == 'test'
        assert maintenance_states[0]['message'] == 'testing'
        assert maintenance_states[0]['level'] == 'warning'

        assert maintenance_states[1]['_id'] == 'danger test'
        assert maintenance_states[1]['message'] == 'apocalypse testing'
        assert maintenance_states[1]['level'] == 'danger'

    def test_unset_maintenance(self):
        maintenance.set_maintenance(_id='test', message='')
        assert MaintenanceState.objects.get(_id='test')
        maintenance.unset_maintenance(_id='test')
        with pytest.raises(MaintenanceState.DoesNotExist):
            MaintenanceState.objects.get(_id='test')
