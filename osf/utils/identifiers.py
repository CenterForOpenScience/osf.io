import abc
import re
from urllib.parse import urljoin

import requests

from framework import sentry
from osf.exceptions import (
    InvalidPIDError,
    InvalidPIDFormatError,
    NoSuchPIDError,
    NoSuchPIDValidatorError,
)
from website.settings import (
    PID_VALIDATION_ENABLED,
    PID_VALIDATION_ENDPOINTS,
)


class PIDValidator(abc.ABC):
    @classmethod
    def for_identifier_category(cls, category):
        for subclass in cls.__subclasses__():
            if subclass.IDENTIFIER_CATEGORY == category:
                return subclass()
        sentry.log_message(
            f"Attempted to validate Identifier with unsupported category {category}."
        )
        raise NoSuchPIDValidatorError(
            f"PID validation not currently supported for PIDs of type {category}"
        )

    def __init__(self):
        self._validation_endpoint = None

    @property
    def validation_endpoint(self):
        if not PID_VALIDATION_ENABLED:
            return None
        return PID_VALIDATION_ENDPOINTS.get(self.IDENTIFIER_CATEGORY)

    @abc.abstractmethod
    def validate(self, pid_value):
        pass


class DOIValidator(PIDValidator):
    IDENTIFIER_CATEGORY = "doi"

    def validate(self, doi_value):
        # Either validation is turned off or we don't know how to validate
        # Either way, just let the people do what they want
        if not self.validation_endpoint:
            return True

        # An Invalid DOI will raise an exception error. Let the caller handle what to do there.
        return self.get_registration_agency(doi_value) is not None

    def get_registration_agency(self, doi_value):
        with requests.get(
            urljoin(self.validation_endpoint, doi_value)
        ) as response:
            response_data = response.json()[0]

        registration_agency = response_data.get("RA")
        if registration_agency:
            return registration_agency

        # These error messages were copied from actual responses;
        # If they change, still raise an error, just not the most descriptive one
        error_status = response_data.get("status")
        if error_status == "DOI does not exist":
            pid_exception = NoSuchPIDError
        elif error_status == "Invalid DOI":
            pid_exception = InvalidPIDFormatError
        else:
            sentry.log_message(
                f"Unexpected response when checking Registration Agency for DOI {doi_value}: "
                f"{response_data}"
            )
            pid_exception = InvalidPIDError

        raise pid_exception(pid_value=doi_value, pid_category="DOI")


def normalize_identifier(pid_value):
    """Extract just the PID Value from a possible full URI."""
    pid_value_expression = "(.*://)?(doi.org/)?(?P<pid_value>.*)"
    return re.match(pid_value_expression, pid_value).group("pid_value")
