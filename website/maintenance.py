from datetime import timedelta

import pytz
from dateutil.parser import parse
from django.utils import timezone

from osf.models.maintenance_state import MaintenanceState


def set_maintenance(start=None, end=None):
    """Set the time period for the maintenance notice to be displayed.
    If no start or end values are given, default to starting now in UTC
    and ending 24 hours from now.

    All given times w/out timezone info will be converted to UTC automatically.

    If you give just an end date, start will default to 24 hours before.
    """
    start = parse(start) if start else timezone.now()
    end = parse(end) if end else start + timedelta(1)

    if not start.tzinfo:
        start = start.replace(tzinfo=pytz.UTC)

    if not end.tzinfo:
        end = end.replace(tzinfo=pytz.UTC)

    if start > end:
        start = end - timedelta(1)

    unset_maintenance()

    state = MaintenanceState.objects.create(
        start=start,
        end=end
    )

    return {'start': state.start, 'end': state.end}


def get_maintenance():
    """Get the current start and end times for the maintenance state.
    Return None if there is no current maintenance state.
    """
    maintenance_state = MaintenanceState.objects.first()

    if maintenance_state:
        return {
            'start': maintenance_state.start.isoformat(),
            'end': maintenance_state.end.isoformat(),
        }
    else:
        return None


def unset_maintenance():
    MaintenanceState.objects.all().delete()
