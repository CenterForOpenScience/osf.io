from unittest import mock
import pytest
from osf.models.user_message import MessageTypes, UserMessage
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory
)

@pytest.mark.django_db
class TestUserMessageInstitutionalAccess:
    """
    Tests for `UserMessage`.
    """

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def noncontrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_with_affiliation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        return user

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def url_with_affiliation(self, user_with_affiliation):
        return f'/{API_BASE}users/{user_with_affiliation._id}/messages/'

    @pytest.fixture()
    def url_without_affiliation(self, user):
        return f'/{API_BASE}users/{user._id}/messages/'

    @pytest.fixture()
    def payload(self, institution, user):
        return {
            'data': {
                'attributes': {
                    'message_text': 'Requesting user access for collaboration',
                    'message_type': MessageTypes.INSTITUTIONAL_REQUEST.value,
                },
                'relationships': {
                    'institution': {
                        'data': {'id': institution._id, 'type': 'institutions'},
                    },
                },
                'type': 'user-message'
            }
        }

    @mock.patch('osf.models.user_message.send_mail')
    def test_institutional_admin_can_create_message(self, mock_send_mail, app, institutional_admin, institution, url_with_affiliation, payload):
        """
        Ensure an institutional admin can create a `UserMessage` with a `message` and `institution`.
        """
        mock_send_mail.return_value = mock.MagicMock()

        res = app.post_json_api(
            url_with_affiliation,
            payload,
            auth=institutional_admin.auth
        )
        assert res.status_code == 201
        data = res.json['data']

        user_message = UserMessage.objects.get(sender=institutional_admin)

        assert user_message.message_text == payload['data']['attributes']['message_text']
        assert user_message.institution == institution

        mock_send_mail.assert_called_once()
        assert mock_send_mail.call_args[1]['to_addr'] == user_message.recipient.username
        assert 'Requesting user access for collaboration' in mock_send_mail.call_args[1]['message_text']
        assert user_message._id == data['id']

    def test_unauthenticated_user_cannot_create_message(self, app, user, url_with_affiliation, payload):
        """
        Ensure that unauthenticated users cannot create a `UserMessage`.
        """
        res = app.post_json_api(url_with_affiliation, payload, expect_errors=True)
        assert res.status_code == 401
        assert 'Authentication credentials were not provided' in res.json['errors'][0]['detail']

    def test_non_institutional_admin_cannot_create_message(self, app, noncontrib, user, url_with_affiliation, payload):
        """
        Ensure a non-institutional admin cannot create a `UserMessage`, even with valid data.
        """
        res = app.post_json_api(url_with_affiliation, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_request_without_institution(self, app, institutional_admin, user, url_with_affiliation, payload):
        """
        Test that a `UserMessage` can be created without specifying an institution, and `institution` is None.
        """
        del payload['data']['relationships']['institution']

        res = app.post_json_api(url_with_affiliation, payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 400
        error = res.json['errors']
        assert error == [
            {
                'source': {
                    'pointer': '/data/relationships/institution'
                },
                'detail': 'Institution ID is required.'
            }
        ]

    def test_missing_message_fails(self, app, institutional_admin, user, url_with_affiliation, payload):
        """
        Ensure a `UserMessage` cannot be created without a `message` attribute.
        """
        del payload['data']['attributes']['message_text']

        res = app.post_json_api(url_with_affiliation, payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 400
        error = res.json['errors']
        assert error == [
            {
                'source': {
                    'pointer': '/data/attributes/message_text'
                },
                'detail': 'This field is required.',
            }
        ]

    def test_admin_cannot_message_user_outside_institution(
            self,
            app,
            institutional_admin,
            url_without_affiliation,
            payload,
            user
    ):
        """
        Ensure that an institutional admin cannot create a `UserMessage` for a user who is not affiliated with their institution.
        """
        res = app.post_json_api(url_without_affiliation, payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Can not send to recipient that is not affiliated with the provided institution.'\
               in res.json['errors'][0]['detail']
