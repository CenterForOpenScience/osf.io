import os
import json
import datetime
import jsonschema

from api.base.exceptions import InvalidModelValueError

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname, path=None):
    if not path:
        path = here
    with open(os.path.join(path, fname)) as f:
        return json.load(f)


def validate_user_json(value, json_schema):
    try:
        jsonschema.validate(value, from_json(json_schema))
    except jsonschema.ValidationError as e:
        if len(e.path) > 1:
            raise InvalidModelValueError("For '{}' the field value {}".format(e.path[-1], e.message))
        raise InvalidModelValueError(e.message)
    except jsonschema.SchemaError as e:
        raise InvalidModelValueError(e.message)

    validate_dates(value)


def validate_dates(info):
    for history in info:

        if history.get('startYear'):
            startDate = datetime.date(history['startYear'], history.get('startMonth', 1), 1)

        if not history['ongoing']:
            if history.get('endYear'):
                endDate = datetime.date(history['endYear'], history.get('endMonth', 1), 1)

            if history.get('startYear') and history.get('endYear'):
                if (endDate - startDate).days <= 0:
                    raise InvalidModelValueError(detail='End date must be greater than or equal to the start date.')
