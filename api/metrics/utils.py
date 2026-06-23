from __future__ import annotations
import re
from urllib.parse import urlsplit

from datetime import timedelta, datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from osf.models import AbstractNode, Guid
from osf.metrics.utils import get_immediate_wrapper


DATE_FORMAT = '%Y-%m-%d'
YEARMONTH_FORMAT = '%Y-%m'

DEFAULT_DAYS_BACK = 13
DEFAULT_MONTHS_BACK = 5 * 30  # days


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


def parse_date_range(
    query_params, is_monthly=False,
) -> tuple[datetime.date | str, datetime.date | str]:
    _from: datetime.date | str | None = None
    _until: datetime.date | str = timezone.now()
    if _days_back := query_params.get('days_back'):
        _from = _until.date() - timedelta(days=int(_days_back))
    elif _timeframe := query_params.get('timeframe'):
        if _match := re.match(r'previous_(\d+)_days?', _timeframe):
            _days_back = int(_match.group(1))
        else:
            raise Exception(f'Unsupported timeframe format: "{_timeframe}"')
        _from = _until - timedelta(days=_days_back)
    elif query_params.get('timeframeStart'):
        _from = query_params.get('timeframeStart')
        _until = query_params.get('timeframeEnd', _until)
    else:
        _from, _until = parse_dates(query_params, is_monthly=is_monthly)
    return (_from, _until)


def _user_has_read_on_resolved_node(user, guid_referent):
    """True if ``user`` has READ on the node this referent belongs to."""
    current = guid_referent
    while current is not None and not isinstance(current, AbstractNode):
        current = get_immediate_wrapper(current)
    if current is None or not isinstance(current, AbstractNode):
        return False
    return current.contributors_and_group_members.filter(guids___id=user._id).exists()


def should_skip_counted_usage(user, *, item_guid=None, pageview_info=None):
    """Return True when this usage should not be recorded."""
    if not getattr(user, 'is_authenticated', False):
        return False

    referents = []
    seen_ids = set()

    def _add_referent(ref):
        if ref is None:
            return
        key = (ref.__class__.__name__, ref.pk)
        if key in seen_ids:
            return
        seen_ids.add(key)
        referents.append(ref)

    if item_guid:
        guid_obj = Guid.load(item_guid)
        if guid_obj and guid_obj.referent:
            _add_referent(guid_obj.referent)

    page_url = (pageview_info or {}).get('page_url')
    if page_url:
        for segment in urlsplit(page_url).path.split('/'):
            if not segment or len(segment) < 5:
                continue
            guid_obj = Guid.load(segment)
            if guid_obj and guid_obj.referent:
                _add_referent(guid_obj.referent)

    return any(_user_has_read_on_resolved_node(user, ref) for ref in referents)
