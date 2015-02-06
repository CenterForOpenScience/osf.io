from nose.tools import *

from tests.base import OsfTestCase


class MendeleyApiTestCase(OsfTestCase):

    def test_request_params(self):
        """All GET requests to Mendeley should have the param "view=all"
        """
        assert_true(False)