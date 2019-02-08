import os
import json
from datetime import datetime
import jsonschema

from api.base.exceptions import InvalidModelValueError

here = os.path.split(os.path.abspath(__file__))[0]

def from_json(fname):
    with open(os.path.join(here, fname)) as f:
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


def validate_dates(history):
    if history.get('start_date'):
        start_date = datetime.strptime(history['start_date'], '%Y-%m-%d')

    if not history.get('ongoing', False):
        if history.get('end_date'):
            end_date = datetime.strptime(history['end_date'], '%Y-%m-%d')

        if history.get('start_date') and history.get('end_date'):
            if (end_date - start_date).days <= 0:
                raise InvalidModelValueError(detail='End date must be greater than or equal to the start date.')
