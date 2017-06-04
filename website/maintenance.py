from datetime import datetime, timedelta

from dateutil.parser import parse

from pymongo.errors import CollectionInvalid
import pytz

from framework.mongo import database

def ensure_maintenance_collection():
    try:
        database.create_collection('maintenance')
    except CollectionInvalid:
        pass

def set_maintenance(start=None, end=None):
    """Set the time period for the maintenance notice to be displayed.
    If no start or end values are given, default to starting now in UTC
    and ending 24 hours from now.

    All given times w/out timezone info will be converted to UTC automatically.

    If you give just an end date, start will default to 24 hours before.
    """
    start = parse(start) if start else datetime.utcnow()
    end = parse(end) if end else start + timedelta(1)

    if not start.tzinfo:
        start = start.replace(tzinfo=pytz.UTC)

    if not end.tzinfo:
        end = end.replace(tzinfo=pytz.UTC)

    if start > end:
        start = end - timedelta(1)

    unset_maintenance()
    # NOTE: We store isoformatted dates in order to preserve timezone information (pymongo retrieves naive datetimes)
    database.maintenance.insert({'maintenance': True, 'start': start.isoformat(), 'end': end.isoformat()})


def get_maintenance():
    """Get the current start and end times for the maintenance state.
    Return None for start and end if there is no maintenance state
    """
    maintenance_state = database.maintenance.find_one({'maintenance': True})
    if maintenance_state:
        return {
            'start': maintenance_state.get('start'),
            'end': maintenance_state.get('end'),
        }
    else:
        return None


def unset_maintenance():
    database['maintenance'].remove()
