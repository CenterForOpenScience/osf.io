import pytest


from addons.boa.boa_error_code import BoaErrorCode
from tests.base import OsfTestCase


class TestBoaErrorCode(OsfTestCase):

    def test_boa_error_code(self):
        assert BoaErrorCode.UNKNOWN == 0
        assert BoaErrorCode.AUTHN_ERROR == 1
        assert BoaErrorCode.QUERY_ERROR == 2
        assert BoaErrorCode.UPLOAD_ERROR_CONFLICT == 3
        assert BoaErrorCode.UPLOAD_ERROR_OTHER == 4
        assert BoaErrorCode.OUTPUT_ERROR == 5


@pytest.mark.django_db
class TestSubmitToBoaAsync(OsfTestCase):
    pass


class TestSubmitToBoa(OsfTestCase):
    pass
