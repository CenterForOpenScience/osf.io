import datetime

import elasticsearch8.dsl as esdsl

from osf.metrics.utils import YearMonth


###
# custom elasticsearch dsl fields

class YearmonthField(esdsl.Date):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, format='strict_year_month')

    def deserialize(self, data):
        if isinstance(data, int):
            # elasticsearch stores dates in milliseconds since the unix epoch
            _as_datetime = datetime.datetime.fromtimestamp(data // 1000)
            return YearMonth.from_date(_as_datetime)
        elif data is None:
            return None
        try:
            return YearMonth.from_any(data)
        except ValueError:
            raise ValueError(f'unsure how to deserialize "{data}" (of type {type(data)}) to YearMonth')

    def serialize(self, data, skip_empty=True):
        if isinstance(data, str):
            return data
        elif isinstance(data, YearMonth):
            return str(data)
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return str(YearMonth.from_date(data))
        elif data is None:
            return None
        else:
            raise ValueError(f'unsure how to serialize "{data}" (of type {type(data)}) as YYYY-MM')
