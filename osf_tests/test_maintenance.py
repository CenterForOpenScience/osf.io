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

    def test_set_maintenance_no_params(self):
        assert not MaintenanceState.objects.exists()
        maintenance.set_maintenance()
        assert MaintenanceState.objects.all().count() == 1

    def test_set_maintenance_twice(self):
        assert not MaintenanceState.objects.exists()
        maintenance.set_maintenance()
        assert MaintenanceState.objects.all().count() == 1
        maintenance.set_maintenance()
        assert MaintenanceState.objects.all().count() == 1

    def test_set_maintenance_with_start_date(self):
        start = timezone.now()
        maintenance.set_maintenance(start=start.isoformat())
        current_state = MaintenanceState.objects.all().first()

        assert current_state.start == start
        assert current_state.end == start + timedelta(1)

    def test_set_maintenance_with_end_date(self):
        end = timezone.now()
        maintenance.set_maintenance(end=end.isoformat())
        current_state = MaintenanceState.objects.all().first()

        assert current_state.start == end - timedelta(1)
        assert current_state.end == end

    def test_get_maintenance(self):
        start = timezone.now()
        maintenance.set_maintenance(start=start.isoformat())
        state = maintenance.get_maintenance()
        assert state['start'] == start.isoformat()
        assert state['end'] == (start + timedelta(1)).isoformat()

    def test_get_maintenance_in_future(self):
        start = (timezone.now() + timedelta(1)).isoformat()
        maintenance.set_maintenance(start=start)
        assert MaintenanceState.objects.exists()
        state = maintenance.get_maintenance()
        assert state['start'] == start

    def test_unset_maintenance(self):
        maintenance.set_maintenance()
        assert MaintenanceState.objects.exists()
        maintenance.unset_maintenance()
        assert not MaintenanceState.objects.exists()
