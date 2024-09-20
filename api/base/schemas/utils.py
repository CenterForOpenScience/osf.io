import datetime
import json
import os

from jsonschema import validate, ValidationError, SchemaError
from jsonschema.validators import Draft7Validator

from api.base.exceptions import InvalidModelValueError

here = os.path.split(os.path.abspath(__file__))[0]


def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)


def validate_user_json(value, json_schema):
    try:
        validate(value, from_json(json_schema), cls=Draft7Validator)
    except ValidationError as e:
        if len(e.path) > 1:
            raise InvalidModelValueError(f"For '{e.path[-1]}' the field value {e.message}")
        raise InvalidModelValueError(e.message)
    except SchemaError as e:
        raise InvalidModelValueError(e.message)

    validate_dates(value)


def validate_dates(info):
    for history in info:

        if history.get('startYear'):
            start_date = datetime.date(history['startYear'], history.get('startMonth', 1), 1)

        if not history.get('ongoing'):
            if history.get('endYear'):
                end_date = datetime.date(history['endYear'], history.get('endMonth', 1), 1)

                if history.get('startYear'):
                    if (end_date - start_date).days <= 0:
                        raise InvalidModelValueError(detail='End date must be greater than or equal to the start date.')
