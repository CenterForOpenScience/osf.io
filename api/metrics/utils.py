import pytz

from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError


def parse_datetimes(query_params):
    now = timezone.now()
    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%dT%H:%M'
    default_days_back = 5

    on_date = query_params.get('on_date', None)
    start_datetime = query_params.get('start_datetime', None)
    end_datetime = query_params.get('end_datetime', None)

    using_time = False
    if (start_datetime and 'T' in start_datetime) or (end_datetime and 'T' in end_datetime):
        using_time = True

    # error if both on_date and a date range
    if on_date and (start_datetime or end_datetime):
        raise ValidationError('You cannot provide both an on date and an end or start datetime.')

    # error if a time is used for a specific date request
    if on_date and 'T' in on_date:
        raise ValidationError('You cannot provide a time for an on_date request.')

    # error if an end_datetime is provided without a start_datetime
    if end_datetime and not start_datetime:
        raise ValidationError('You cannot provide a specific end_datetime with no start_datetime')

    if on_date:
        start_datetime = datetime.strptime(on_date, date_format)
        end_datetime = start_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

    else:
        # default date range: 6 days ago to 1 day ago, at midnight
        default_start = (now - timedelta(default_days_back + 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        default_end = (now - timedelta(1)).replace(hour=23, minute=59, second=59, microsecond=999)

        format_to_use = datetime_format if using_time else date_format
        try:
            start_datetime = datetime.strptime(start_datetime, format_to_use).replace(tzinfo=pytz.utc) if start_datetime else default_start
            end_datetime = datetime.strptime(end_datetime, format_to_use).replace(tzinfo=pytz.utc) if end_datetime else default_end
        except ValueError:
            raise ValidationError('You cannot use a mixture of date format and datetime format.')
        # if not using time, make sure to ensure start date is at midnight, and end_date is 11:59
        if not using_time:
            start_datetime = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            end_datetime = end_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

    if start_datetime > end_datetime:
        raise ValidationError('The end_datetime must be after the start_datetime')

    return start_datetime, end_datetime
