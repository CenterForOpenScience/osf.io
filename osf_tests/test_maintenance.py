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

    def test_set_maintenance_twice(self):
        assert not MaintenanceState.objects.exists()
        maintenance.set_maintenance(message='')
        assert MaintenanceState.objects.all().count() == 1
        maintenance.set_maintenance(message='')
        assert MaintenanceState.objects.all().count() == 1

    def test_set_maintenance_with_start_date(self):
        start = timezone.now()
        maintenance.set_maintenance(message='', start=start.isoformat())
        current_state = MaintenanceState.objects.all().first()

        assert current_state.start == start
        assert current_state.end == start + timedelta(1)

    def test_set_maintenance_with_end_date(self):
        end = timezone.now()
        maintenance.set_maintenance(message='', end=end.isoformat())
        current_state = MaintenanceState.objects.all().first()

        assert current_state.start == end - timedelta(1)
        assert current_state.end == end

    def test_set_maintenance_in_future(self):
        start = (timezone.now() + timedelta(1))
        maintenance.set_maintenance(message='', start=start.isoformat())
        current_state = MaintenanceState.objects.all().first()

        assert current_state.start == start
        assert current_state.end == start + timedelta(1)

    def test_set_maintenance_level(self):
        maintenance.set_maintenance(message='')
        assert MaintenanceState.objects.all().first().level == 1
        maintenance.unset_maintenance()

        maintenance.set_maintenance(message='', level=3)
        assert MaintenanceState.objects.all().first().level == 3
        maintenance.unset_maintenance()

    def test_unset_maintenance(self):
        maintenance.set_maintenance(message='')
        assert MaintenanceState.objects.exists()
        maintenance.unset_maintenance()
        assert not MaintenanceState.objects.exists()
