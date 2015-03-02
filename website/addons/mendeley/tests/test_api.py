from nose.tools import *

import mock
import mendeley
import time
import datetime

from tests.base import OsfTestCase

from website.util import web_url_for
from website.addons.mendeley import model
from website.addons.mendeley.api import APISession


class MendeleyApiTestCase(OsfTestCase):

    def setUp(self):
        super(MendeleyApiTestCase, self).setUp()
        self.provider = model.Mendeley()
        self.mock_partial = mendeley.Mendeley(
            client_id='1234567890',
            client_secret='1a2s3d4f5g',
            redirect_uri='/api/v1/some/fake/url/mendeley'
        )
        self.mock_credentials = {
            'access_token': '1234567890987654321',
            'refresh_token': 'asdfghjklkjhgfdsa',
            'expires_at': time.mktime((datetime.datetime.utcnow() + datetime.timedelta(days=10)).timetuple()),
            'token_type': 'bearer',
        }

    @mock.patch('website.addons.mendeley.api.MendeleySession.request')
    def test_request_params(self, mock_request):
        # All GET requests to Mendeley should have the param "view=all"
        client = APISession(self.mock_partial, self.mock_credentials)
        client.request()
        args, kwargs = mock_request.call_args
        assert_equal(kwargs['params'], {'view': 'all'})
