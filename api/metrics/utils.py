import re

import pytz

from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError


DATETIME_FORMAT = '%Y-%m-%dT%H:%M'
DATE_FORMAT = '%Y-%m-%d'
YEARMONTH_FORMAT = '%Y-%m'

DEFAULT_DAYS_BACK = 5
DEFAULT_MONTHS_BACK = 5 * 30  # days


def parse_datetimes(query_params):
    now = timezone.now()

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
        start_datetime = datetime.strptime(on_date, DATE_FORMAT)
        end_datetime = start_datetime.replace(hour=23, minute=59, second=59, microsecond=999)

    else:
        # default date range: 6 days ago to 1 day ago, at midnight
        default_start = (now - timedelta(DEFAULT_DAYS_BACK + 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        default_end = (now - timedelta(1)).replace(hour=23, minute=59, second=59, microsecond=999)

        format_to_use = DATETIME_FORMAT if using_time else DATE_FORMAT
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


def parse_date_param(param_value, is_monthly=False):
    if is_monthly:
        date = datetime.strptime(param_value, DATE_FORMAT).date()
        return f'{date.year}-{date.month:>02}'
    return datetime.strptime(param_value, DATE_FORMAT).date()


def parse_dates(query_params, is_monthly=False):
    default_time_back = DEFAULT_MONTHS_BACK if is_monthly else DEFAULT_DAYS_BACK
    start_date_param = query_params.get('start_date', None)
    end_date_param = query_params.get('end_date', None)

    if end_date_param and not start_date_param:
        raise ValidationError('You cannot provide a specific end_date with no start_date')

    if not start_date_param:
        start_date_param = (timezone.now() - timedelta(days=default_time_back)).date()
    if not end_date_param:
        end_date_param = timezone.now().date()

    start_date = parse_date_param(str(start_date_param), is_monthly)
    end_date = parse_date_param(str(end_date_param), is_monthly)

    if start_date > end_date:
        raise ValidationError('The end_date must be after the start_date')

    return start_date, end_date


def parse_date_range(query_params, is_monthly=False):
    if query_params.get('days_back', None):
        days_back = query_params.get('days_back', DEFAULT_DAYS_BACK)
        report_date_range = {'gte': f'now/d-{days_back}d'}
    elif query_params.get('timeframe', False):
        timeframe = query_params.get('timeframe')
        if timeframe is not None:
            m = re.match(r'previous_(\d+)_days?', timeframe)
            if m:
                days_back = m.group(1)
            else:
                raise Exception(f'Unsupported timeframe format: "{timeframe}"')
            report_date_range = {'gte': f'now/d-{days_back}d'}
    elif query_params.get('timeframeStart'):
        tsStart = query_params.get('timeframeStart')
        tsEnd = query_params.get('timeframeEnd')
        report_date_range = {'gte': tsStart, 'lt': tsEnd}
    else:
        start_date, end_date = parse_dates(query_params, is_monthly=is_monthly)
        report_date_range = {'gte': str(start_date), 'lte': str(end_date)}
    return report_date_range
