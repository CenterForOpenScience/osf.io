import pytest

from django.core.exceptions import ValidationError as DjangoValidationError

from osf.exceptions import reraise_django_validation_errors, ValidationError
from tests.base import OsfTestCase


class TestExceptions(OsfTestCase):

    def test_reraise_django_validation_error(self):
        with pytest.raises(ValidationError) as excinfo:
            with reraise_django_validation_errors():
                raise DjangoValidationError('derp')

        assert excinfo.value.args[0] == 'derp'
        assert excinfo.value.message == 'derp'

        with pytest.raises(ValidationError) as excinfo:
            with reraise_django_validation_errors():
                raise DjangoValidationError({'foo': ['derp']})

        assert excinfo.value.message_dict == {'foo': ['derp']}
