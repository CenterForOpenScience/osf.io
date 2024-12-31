from unittest import mock
import pytest
from osf.models.user_message import MessageTypes, UserMessage
from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory
)
from website.mails import USER_MESSAGE_INSTITUTIONAL_ACCESS_REQUEST
from webtest import AppError


@pytest.mark.django_db
class TestUserMessageInstitutionalAccess:
    """
    Tests for `UserMessage`.
    """

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory(can_request_access=True)

    @pytest.fixture()
    def institution_without_access(self):
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
    def user_with_affiliation_on_institution_without_access(self, institution_without_access):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution_without_access)
        return user

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def institutional_admin_on_institution_without_access(self, institution_without_access):
        admin_user = AuthUserFactory()
        institution_without_access.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def url_with_affiliation(self, user_with_affiliation):
        return f'/{API_BASE}users/{user_with_affiliation._id}/messages/'

    @pytest.fixture()
    def url_with_affiliation_on_institution_without_access(self, user_with_affiliation_on_institution_without_access):
        return f'/{API_BASE}users/{user_with_affiliation_on_institution_without_access._id}/messages/'

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

    @mock.patch('osf.models.user_message.send_mail')
    def test_institutional_admin_can_not_create_message(self, mock_send_mail, app, institutional_admin_on_institution_without_access,
                                                        institution_without_access,url_with_affiliation_on_institution_without_access,
                                                        payload):
        """
        Ensure an institutional admin cannot create a `UserMessage` with a `message` and `institution` witch has 'can_request_access' as False
        """
        mock_send_mail.return_value = mock.MagicMock()

        # Use pytest.raises to explicitly expect the 403 error
        with pytest.raises(AppError) as exc_info:
            app.post_json_api(
                url_with_affiliation_on_institution_without_access,
                payload,
                auth=institutional_admin_on_institution_without_access.auth
            )

        # Assert that the raised error contains the 403 Forbidden status
        assert '403 Forbidden' in str(exc_info.value)

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
                'detail': 'Institution is required.'
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
        assert res.status_code == 409
        assert ('Cannot send to a recipient that is not affiliated with the provided institution.'
                in res.json['errors'][0]['detail']['user'])

    @mock.patch('osf.models.user_message.send_mail')
    def test_cc_institutional_admin(
            self,
            mock_send_mail,
            app,
            institutional_admin,
            institution,
            url_with_affiliation,
            user_with_affiliation,
            payload
    ):
        """
        Ensure CC option works as expected, sending messages to all institutional admins except the sender.
        """
        mock_send_mail.return_value = mock.MagicMock()

        # Enable CC in the payload
        payload['data']['attributes']['bcc_sender'] = True

        # Perform the API request
        res = app.post_json_api(
            url_with_affiliation,
            payload,
            auth=institutional_admin.auth,
        )
        assert res.status_code == 201
        user_message = UserMessage.objects.get()

        assert user_message.is_sender_BCCed
        # Two emails are sent during the CC but this is how the mock works `send_email` is called once.
        mock_send_mail.assert_called_once_with(
            to_addr=user_with_affiliation.username,
            bcc_addr=[institutional_admin.username],
            reply_to=None,
            message_text='Requesting user access for collaboration',
            mail=USER_MESSAGE_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            sender=institutional_admin,
            recipient=user_with_affiliation,
            institution=institution,
        )

    @mock.patch('osf.models.user_message.send_mail')
    def test_cc_field_defaults_to_false(self, mock_send_mail, app, institutional_admin, url_with_affiliation, user_with_affiliation, institution, payload):
        """
        Ensure the `cc` field defaults to `false` when not provided in the payload.
        """
        res = app.post_json_api(url_with_affiliation, payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        user_message = UserMessage.objects.get(sender=institutional_admin)
        assert user_message.message_text == payload['data']['attributes']['message_text']
        mock_send_mail.assert_called_once_with(
            to_addr=user_with_affiliation.username,
            bcc_addr=None,
            reply_to=None,
            message_text='Requesting user access for collaboration',
            mail=USER_MESSAGE_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            sender=institutional_admin,
            recipient=user_with_affiliation,
            institution=institution,
        )

    @mock.patch('osf.models.user_message.send_mail')
    def test_reply_to_header_set(self, mock_send_mail, app, institutional_admin, user_with_affiliation, institution, url_with_affiliation, payload):
        """
        Ensure that the 'Reply-To' header is correctly set to the sender's email address.
        """
        payload['data']['attributes']['reply_to'] = True

        res = app.post_json_api(
            url_with_affiliation,
            payload,
            auth=institutional_admin.auth,
        )
        assert res.status_code == 201

        mock_send_mail.assert_called_once_with(
            to_addr=user_with_affiliation.username,
            bcc_addr=None,
            reply_to=institutional_admin.username,
            message_text='Requesting user access for collaboration',
            mail=USER_MESSAGE_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            sender=institutional_admin,
            recipient=user_with_affiliation,
            institution=institution,
        )
