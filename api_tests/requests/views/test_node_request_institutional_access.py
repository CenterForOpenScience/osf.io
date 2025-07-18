import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin

from osf_tests.factories import NodeFactory, InstitutionFactory, AuthUserFactory
from osf.utils.workflows import DefaultStates, NodeRequestTypes
from framework.auth import Auth


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_notification_send')
class TestNodeRequestListInstitutionalAccess(NodeRequestTestMixin):

    @pytest.fixture()
    def url(self, project):
        return f'/{API_BASE}nodes/{project._id}/requests/'

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory(institutional_request_access_enabled=True)

    @pytest.fixture()
    def institution_without_access(self):
        return InstitutionFactory()

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
    def user_without_affiliation(self):
        return AuthUserFactory()

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
    def create_payload(self, institution, user_with_affiliation):
        return {
            'data': {
                'attributes': {
                    'comment': 'Wanna Philly Philly?',
                    'request_type': NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
                },
                'relationships': {
                    'institution': {
                        'data': {
                            'id': institution._id,
                            'type': 'institutions'
                        }
                    },
                    'message_recipient': {
                        'data': {
                            'id': user_with_affiliation._id,
                            'type': 'users'
                        }
                    }
                },
                'type': 'node-requests'
            }
        }

    @pytest.fixture()
    def create_payload_on_institution_without_access(self, institution_without_access, user_with_affiliation_on_institution_without_access):
        return {
            'data': {
                'attributes': {
                    'comment': 'Wanna Philly Philly?',
                    'request_type': NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
                },
                'relationships': {
                    'institution': {
                        'data': {
                            'id': institution_without_access._id,
                            'type': 'institutions'
                        }
                    },
                    'message_recipient': {
                        'data': {
                            'id': user_with_affiliation_on_institution_without_access._id,
                            'type': 'users'
                        }
                    }
                },
                'type': 'node-requests'
            }
        }

    @pytest.fixture()
    def create_payload_non_institutional_access(self, institution_without_access, user_with_affiliation_on_institution_without_access):
        return {
            'data': {
                'attributes': {
                    'comment': 'Wanna Philly Philly?',
                    'request_type': NodeRequestTypes.ACCESS.value,
                },
                'type': 'node-requests'
            }
        }

    @pytest.fixture()
    def node_with_disabled_access_requests(self, institution):
        node = NodeFactory()
        node.access_requests_enabled = False
        creator = node.creator
        creator.add_or_update_affiliated_institution(institution)
        creator.save()
        node.add_affiliated_institution(institution, creator)
        node.save()
        return node

    def test_institutional_admin_can_make_institutional_request(self, app, project, institutional_admin, url, create_payload):
        """
        Test that an institutional admin can make an institutional access request.
        """
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        # Verify the NodeRequest object is created
        node_request = project.requests.get(creator=institutional_admin)
        assert node_request.request_type == NodeRequestTypes.INSTITUTIONAL_REQUEST.value
        assert node_request.comment == 'Wanna Philly Philly?'
        assert node_request.machine_state == DefaultStates.PENDING.value

    def test_non_admin_cant_make_institutional_request(self, app, project, noncontrib, url, create_payload):
        """
        Test that a non-institutional admin cannot make an institutional access request.
        """
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'You do not have permission to perform this action for this institution.' in res.json['errors'][0]['detail']

    def test_institutional_admin_can_add_requested_permission(self, app, project, institutional_admin, url, create_payload):
        """
        Test that an institutional admin can make an institutional access request with requested_permissions.
        """
        create_payload['data']['attributes']['requested_permissions'] = 'admin'

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        # Verify the NodeRequest object is created with the correct requested_permissions
        node_request = project.requests.get(creator=institutional_admin)
        assert node_request.request_type == NodeRequestTypes.INSTITUTIONAL_REQUEST.value
        assert node_request.requested_permissions == 'admin'

    def test_institutional_admin_can_not_add_requested_permission(self, app, project, institutional_admin_on_institution_without_access, url, create_payload_on_institution_without_access):
        """
        Test that an institutional admin can not make an institutional access request on institution with disabled access .
        """
        create_payload_on_institution_without_access['data']['attributes']['requested_permissions'] = 'admin'

        res = app.post_json_api(
            url, create_payload_on_institution_without_access, auth=institutional_admin_on_institution_without_access.auth, expect_errors=True
        )

        assert res.status_code == 403

    def test_institutional_admin_needs_institution(self, app, project, institutional_admin, url, create_payload):
        """
        Test that the payload needs the institution relationship and gives the correct error message.
        """
        del create_payload['data']['relationships']['institution']

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Institution is required.' in res.json['errors'][0]['detail']

    def test_institutional_admin_invalid_institution(self, app, project, institutional_admin, url, create_payload):
        """
        Test that the payload validates the institution relationship and gives the correct error message when it's
        invalid.
        """
        create_payload['data']['relationships']['institution']['data']['id'] = 'invalid_id'

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Institution is does not exist.' in res.json['errors'][0]['detail']

    def test_institutional_admin_unauth_institution(self, app, project, institution_without_access, institutional_admin, url, create_payload):
        """
        Test that the view authenticates the relationship between the institution and the user and gives the correct
        error message when it's unauthorized
        """
        create_payload['data']['relationships']['institution']['data']['id'] = institution_without_access._id

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'Institutional request access is not enabled.' in res.json['errors'][0]['detail']

    def test_email_not_sent_without_recipient(self, mock_notification_send, app, project, institutional_admin, url,
                                                 create_payload, institution):
        """
        Test that an email is not sent when no recipient is listed when an institutional access request is made,
        but the request is still made anyway without email.
        """
        del create_payload['data']['relationships']['message_recipient']
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        # Check that an email is sent
        assert not mock_notification_send.called

    def test_email_not_sent_outside_institution(self, mock_notification_send, app, project, institutional_admin, url,
                                                 create_payload, user_without_affiliation, institution):
        """
        Test that you are prevented from requesting a user with the correct institutional affiliation.
        """
        create_payload['data']['relationships']['message_recipient']['data']['id'] = user_without_affiliation._id
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert f'User {user_without_affiliation._id} is not affiliated with the institution.' in res.json['errors'][0]['detail']

        # Check that an email is sent
        assert not mock_notification_send.called

    def test_email_sent_on_creation(
            self,
            mock_notification_send,
            app,
            project,
            institutional_admin,
            url,
            user_with_affiliation,
            create_payload,
            institution
    ):
        """
        Test that an email is sent to the appropriate recipients when an institutional access request is made.
        """
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_notification_send.call_count == 1

    def test_bcc_institutional_admin(
            self,
            mock_notification_send,
            app,
            project,
            institutional_admin,
            url,
            user_with_affiliation,
            create_payload,
            institution
    ):
        """
        Ensure BCC option works as expected, sending messages to sender giving them a copy for themselves.
        """
        create_payload['data']['attributes']['bcc_sender'] = True
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_notification_send.call_count == 1

    def test_reply_to_institutional_admin(
            self,
            mock_notification_send,
            app,
            project,
            institutional_admin,
            url,
            user_with_affiliation,
            create_payload,
            institution
    ):
        """
        Ensure reply-to option works as expected, allowing a reply to header be added to the email.
        """
        create_payload['data']['attributes']['reply_to'] = True
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_notification_send.call_count == 1

    def test_access_requests_disabled_raises_permission_denied(
        self, app, node_with_disabled_access_requests, user_with_affiliation, institutional_admin, create_payload
    ):
        """
        Ensure that when `access_requests_enabled` is `False`, a PermissionDenied error is raised.
        """
        res = app.post_json_api(
            f'/{API_BASE}nodes/{node_with_disabled_access_requests._id}/requests/',
            create_payload,
            auth=institutional_admin.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert f"{node_with_disabled_access_requests._id} does not have Access Requests enabled" in res.json['errors'][0]['detail']

    def test_placeholder_text_when_comment_is_empty(
            self,
            mock_notification_send,
            app,
            project,
            institutional_admin,
            url,
            user_with_affiliation,
            create_payload,
            institution
    ):
        """
        Test that the placeholder text is used when the comment field is empty or None.
        """
        # Test with empty comment
        create_payload['data']['attributes']['comment'] = ''
        mock_notification_send.reset_mock()
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        mock_notification_send.assert_called()

    def test_requester_can_resubmit(self, app, project, institutional_admin, url, create_payload):
        """
        Test that a requester can submit another access request for the same node.
        """
        # Create the first request
        app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        node_request = project.requests.get()
        node_request.run_reject(project.creator, 'test comment2')
        node_request.refresh_from_db()
        assert node_request.machine_state == 'rejected'

        # Attempt to create a second request
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'

    def test_requester_can_make_insti_request_after_access_resubmit(self, app, project, institutional_admin, url, create_payload_non_institutional_access, create_payload):
        """
        Test that a requester can submit another access request, then institutional access for the same node.
        """
        # Create the first request a basic request_type == `access` request
        app.post_json_api(url, create_payload_non_institutional_access, auth=institutional_admin.auth)
        node_request = project.requests.get()
        node_request.run_reject(project.creator, 'test comment2')
        node_request.refresh_from_db()
        assert node_request.machine_state == 'rejected'

        # Attempt to create a second request, refresh and update as institutional
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'

    def test_requester_can_resubmit_after_approval(self, app, project, institutional_admin, url, create_payload):
        """
        Test that a requester can submit another access request for the same node.
        """
        # Create the first request
        app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        node_request = project.requests.get()
        node_request.run_accept(project.creator, 'test comment2')
        node_request.refresh_from_db()
        assert node_request.machine_state == 'accepted'

        project.remove_contributor(node_request.creator, Auth(node_request.creator))
        node_request = project.requests.get()

        # Attempt to create a second request
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'

    def test_requester_can_resubmit_after_2_approvals(self, app, project, institutional_admin, url, create_payload):
        """
        Test that a requester can submit another access request for the same node.
        """
        # Create the first request
        app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        node_request = project.requests.get()
        node_request.run_accept(project.creator, 'test comment2')
        node_request.refresh_from_db()
        assert node_request.machine_state == 'accepted'

        project.remove_contributor(node_request.creator, Auth(node_request.creator))

        # Attempt to create a second request
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'

        # Accepted request can violate node, but we will just update the current one
        assert project.requests.all().count() == 1

        # Attempt to create a second request
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'pending'
        assert project.requests.all().count() == 1
