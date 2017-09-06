import pytest

from rest_framework import status

from api.base.settings import API_BASE

from api_tests.cas.util import fake, make_request_payload_register_external

from osf.models import OSFUser

from osf_tests.factories import UserFactory, UnconfirmedUserFactory

# TODO 1: how to mock methods and check if they are called


@pytest.mark.django_db
class TestAccountRegisterExternal(object):

    @pytest.fixture()
    def endpoint_url(self):
        return '/{0}cas/account/register/external/'.format(API_BASE)

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def unconfirmed_user(self):
        return UnconfirmedUserFactory()

    @pytest.fixture()
    def external_id_provider(self):
        return "ORCID"

    @pytest.fixture()
    def external_id(self):
        return fake.numerify('####-####-####-####')

    @pytest.fixture()
    def new_user_email(self):
        return fake.email()

    @pytest.fixture()
    def attributes(self):
        return  {
            'given-names': 'User001',
            'family-name': 'Test',
        }

    def test_create_external_user_if_not_found(self, app, endpoint_url, new_user_email, external_id, external_id_provider):

        assert OSFUser.objects.filter(username=new_user_email).count() == 0

        payload = make_request_payload_register_external(new_user_email, external_id, external_id_provider, {})
        res = app.post(endpoint_url, payload)
        assert res.status_code == status.HTTP_200_OK

        try:
            user = OSFUser.objects.filter(username=new_user_email).get()
        except OSFUser.DoesNotExist:
            user = None

        assert user is not None
        assert user.is_confirmed is False
        assert user.external_identity.get(external_id_provider).get(external_id) == 'CREATE'
        assert user.get_confirmation_token(new_user_email) is not None

        expected_response = {
            'username': user.username,
            'createOrLink': 'CREATE',
        }
        assert res.json == expected_response

    def test_create_external_user_if_not_confirmed(self, app, endpoint_url, unconfirmed_user, attributes, external_id, external_id_provider):

        payload = make_request_payload_register_external(unconfirmed_user.username, external_id, external_id_provider, attributes)
        res = app.post(endpoint_url, payload)
        unconfirmed_user.reload()

        assert res.status_code == status.HTTP_200_OK
        assert unconfirmed_user.external_identity.get(external_id_provider).get(external_id) == 'CREATE'
        assert unconfirmed_user.get_confirmation_token(unconfirmed_user.username) is not None

        expected_response = {
            'username': unconfirmed_user.username,
            'createOrLink': 'CREATE',
        }
        assert res.json == expected_response

        assert unconfirmed_user.fullname == '{} {}'.format(attributes.get('given-names'), attributes.get('family-name'))

    def test_create_external_user_if_disabled(self, app, endpoint_url, user, external_id, external_id_provider):

        user.disable_account()
        user.save()
        user.reload()

        payload = make_request_payload_register_external(user.username, external_id, external_id_provider, {})
        res = app.post(endpoint_url, payload, expect_errors=True)

        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40008

    def test_link_external_user_if_active(self, app, endpoint_url, user, external_id, external_id_provider):

        payload = make_request_payload_register_external(user.username, external_id, external_id_provider, {})
        res = app.post(endpoint_url, payload)
        user.reload()

        assert res.status_code == status.HTTP_200_OK
        assert user.external_identity.get(external_id_provider).get(external_id) == 'LINK'
        assert user.get_confirmation_token(user.username) is not None

        expected_response = {
            'username': user.username,
            'createOrLink': 'LINK',
        }
        assert res.json == expected_response

    def test_create_or_link_external_identity_already_claimed(self, app, endpoint_url, user, new_user_email, external_id, external_id_provider):

        user.external_identity = {
            external_id_provider: {
                external_id: 'VERIFIED'
            }
        }
        user.save()

        payload = make_request_payload_register_external(new_user_email, external_id, external_id_provider, {})
        res = app.post(endpoint_url, payload, expect_errors=True)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert len(res.json.get('errors')) == 1
        assert res.json.get('errors')[0].get('code') == 40015
