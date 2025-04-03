import copy
import time
import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import RegistrationFactory
from framework.auth import signing


@pytest.mark.django_db
class TestRegistrationCallbacks:

    @pytest.fixture()
    def registration(self):
        registration = RegistrationFactory()
        return registration

    @pytest.fixture()
    def url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/callbacks/'

    @pytest.fixture()
    def payload(self):
        return {
            "action": "copy",
            "destination": {
                "name": "Archive of OSF Storage",
            },
            "errors": None,
            "source": {
                "provider": "osfstorage",
            },
            "time": time.time() + 1000
        }

    def sign_payload(self, payload):
        message, signature = signing.default_signer.sign_payload(payload)
        return {
            'payload': message,
            'signature': signature,
        }

    def test_registration_callback(self, app, payload, url):
        data = self.sign_payload(payload)
        res = app.put_json(url, data)
        assert res.status_code == 200

    def test_signature_expired(self, app, payload, url):
        payload['time'] = time.time() - 100
        data = self.sign_payload(payload)
        res = app.put_json(url, data, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Signature has expired'

    def test_bad_signature(self, app, payload, url):
        data = self.sign_payload(payload)
        data['signature'] = '1234'
        res = app.put_json(url, data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_invalid_payload(self, app, payload, url):
        payload1 = copy.deepcopy(payload)
        del payload1['time']
        data = self.sign_payload(payload1)
        res = app.put_json(url, data, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'

        payload2 = copy.deepcopy(payload)
        data = self.sign_payload(payload2)
        del data['signature']
        res = app.put_json(url, data, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'

        payload3 = copy.deepcopy(payload)
        data = self.sign_payload(payload3)
        del data['payload']
        res = app.put_json(url, data, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid Payload'
