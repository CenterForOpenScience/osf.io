import abc
from urllib.parse import urljoin

import requests

from osf.exceptions import (
    InvalidPIDError,
    InvalidPIDFormatError,
    NoSuchPIDError,
    NoSuchPIDValidatorError
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
        raise NoSuchPIDValidatorError(
            f'PID validation not currently supported for PIDs of type {category}'
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

    IDENTIFIER_CATEGORY = 'doi'

    def validate(self, doi_value):
        #Local-development and test environments should
        if not self.validation_endpoint:
            return True
        # An Invalid DOI will not have a Registration Agency
        return self.get_registration_agency(doi_value) is not None

    def get_registration_agency(self, doi_value):
        with requests.get(urljoin(self.validation_endpoint, doi_value)) as response:
            response_data = response.json()[0]

        registration_agency = response_data.get('RA')
        if registration_agency:
            return registration_agency

        # These error messages were copied from actual responses;
        # If they change, still raise an error, just not the most descriptive one
        error_status = response_data.get('status')
        if error_status == 'DOI does not exist':
            pid_exception = NoSuchPIDError
        elif error_status == 'Invalid DOI':
            pid_exception = InvalidPIDFormatError
        else:
            pid_exception = InvalidPIDError

        raise pid_exception(pid_value=doi_value, pid_category='DOI')
