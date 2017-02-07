import datetime
import mock
from nose.tools import assert_equal
import pytest
import time

from django.utils import timezone
import mendeley

from addons.mendeley import models
from tests.base import OsfTestCase
from addons.mendeley.api import APISession

pytestmark = pytest.mark.django_db

class MendeleyApiTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyApiTestCase, self).setUp()
        self.provider = models.Mendeley()
        self.mock_partial = mendeley.Mendeley(
            client_id='1234567890',
            client_secret='1a2s3d4f5g',
            redirect_uri='/api/v1/some/fake/url/mendeley'
        )
        self.mock_credentials = {
            'access_token': '1234567890987654321',
            'refresh_token': 'asdfghjklkjhgfdsa',
            'expires_at': time.mktime((timezone.now() + datetime.timedelta(days=10)).timetuple()),
            'token_type': 'bearer',
        }

    @mock.patch('addons.mendeley.api.MendeleySession.request')
    def test_request_params(self, mock_request):
        # All GET requests to Mendeley should have the param "view=all"
        client = APISession(self.mock_partial, self.mock_credentials)
        client.request()
        args, kwargs = mock_request.call_args
        assert_equal(kwargs['params'], {'view': 'all', 'limit': '500'})
