from datetime import timedelta

import pytz
from dateutil.parser import parse
from django.utils import timezone

from api.base.serializers import MaintenanceStateSerializer
from osf.models.maintenance_state import MaintenanceState


def set_maintenance(_id, message, level=1, start=None, end=None):
    """Creates maintenance state obj with the given params.

    Set the time period for the maintenance notice to be displayed.
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

    state = MaintenanceState.objects.create(
        _id=_id,
        message=message,
        level=level,
        start=start,
        end=end
    )

    return {
        '_id': state._id,
        'start': state.start,
        'end': state.end
    }

def get_maintenance_states():
    """Get the current start and end times for the maintenance state.
    Return None if there is no current maintenance state.
    """
    return [
        MaintenanceStateSerializer(maintenance).data
        for maintenance in MaintenanceState.objects.all()
    ]

def unset_maintenance(_id):
    MaintenanceState.objects.get(_id=_id).delete()
