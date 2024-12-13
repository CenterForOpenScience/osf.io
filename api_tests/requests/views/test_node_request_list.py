from unittest import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin

from osf_tests.factories import (
    NodeFactory,
    NodeRequestFactory,
    InstitutionFactory,
    AuthUserFactory
)
from osf.utils.workflows import DefaultStates, NodeRequestTypes
from website.mails import NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST


@pytest.mark.django_db
class TestNodeRequestListCreate(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, project):
        return f'/{API_BASE}nodes/{project._id}/requests/'

    @pytest.fixture()
    def create_payload(self):
        return {
            'data': {
                'attributes': {
                    'comment': 'ASDFG',
                    'request_type': NodeRequestTypes.ACCESS.value
                },
                'type': 'node-requests'
            }
        }

    def test_noncontrib_can_submit_to_public_node(self, app, project, noncontrib, url, create_payload):
        project.is_public = True
        project.save()
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201

    def test_noncontrib_can_submit_to_private_node(self, app, project, noncontrib, url, create_payload):
        assert not project.is_public
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201

    def test_must_be_logged_in_to_create(self, app, url, create_payload):
        res = app.post_json_api(url, create_payload, expect_errors=True)
        assert res.status_code == 401

    def test_contributor_cannot_submit_to_contributed_node(self, app, url, write_contrib, create_payload):
        res = app.post_json_api(url, create_payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You cannot request access to a node you contribute to.'

    def test_admin_can_view_requests(self, app, url, admin, node_request):
        res = app.get(url, auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data'][0]['id'] == node_request._id

    def test_write_contrib_cannot_view_requests(self, app, url, write_contrib, node_request):
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_requester_cannot_view_requests(self, app, url, requester, node_request):
        res = app.get(url, auth=requester.auth, expect_errors=True)
        assert res.status_code == 403

    def test_noncontrib_cannot_view_requests(self, app, url, noncontrib, node_request):
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_requester_cannot_submit_again(self, app, url, requester, node_request, create_payload):
        res = app.post_json_api(url, create_payload, auth=requester.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Users may not have more than one access request per node.'

    def test_requests_disabled_create(self, app, url, create_payload, project, noncontrib):
        project.access_requests_enabled = False
        project.save()
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403

    def test_requests_disabled_list(self, app, url, create_payload, project, admin):
        project.access_requests_enabled = False
        project.save()
        res = app.get(url, create_payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 403

    @mock.patch('website.mails.mails.send_mail')
    def test_email_sent_to_all_admins_on_submit(self, mock_mail, app, project, noncontrib, url, create_payload, second_admin):
        project.is_public = True
        project.save()
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 2

    @mock.patch('website.mails.mails.send_mail')
    def test_email_not_sent_to_parent_admins_on_submit(self, mock_mail, app, project, noncontrib, url, create_payload, second_admin):
        component = NodeFactory(parent=project, creator=second_admin)
        component.is_public = True
        project.save()
        url = f'/{API_BASE}nodes/{component._id}/requests/'
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        assert component.parent_admin_contributors.count() == 1
        assert component.contributors.count() == 1
        assert mock_mail.call_count == 1

    def test_request_followed_by_added_as_contrib(elf, app, project, noncontrib, admin, url, create_payload):
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        assert project.requests.filter(creator=noncontrib, machine_state='pending').exists()

        project.add_contributor(noncontrib, save=True)
        assert project.is_contributor(noncontrib)
        assert not project.requests.filter(creator=noncontrib, machine_state='pending').exists()
        assert project.requests.filter(creator=noncontrib, machine_state='accepted').exists()

    def test_filter_by_machine_state(self, app, project, noncontrib, url, admin, node_request):
        initial_node_request = NodeRequestFactory(
            creator=noncontrib,
            target=project,
            request_type=NodeRequestTypes.ACCESS.value,
            machine_state=DefaultStates.INITIAL.value
        )
        filtered_url = f'{url}?filter[machine_state]=pending'
        res = app.get(filtered_url, auth=admin.auth)
        assert res.status_code == 200
        ids = [result['id'] for result in res.json['data']]
        assert initial_node_request._id not in ids
        assert node_request.machine_state == 'pending' and node_request._id in ids

@pytest.mark.django_db
class TestNodeRequestListInstitutionalAccess(NodeRequestTestMixin):

    @pytest.fixture()
    def url(self, project):
        return f'/{API_BASE}nodes/{project._id}/requests/'

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution2(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_with_affiliation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
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

    def test_institutional_admin_unauth_institution(self, app, project, institution2, institutional_admin, url, create_payload):
        """
        Test that the view authenticates the relationship between the institution and the user and gives the correct
        error message when it's unauthorized.'
        """
        create_payload['data']['relationships']['institution']['data']['id'] = institution2._id

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'You do not have permission to perform this action for this institution.' in res.json['errors'][0]['detail']

    @mock.patch('api.requests.serializers.send_mail')
    def test_email_not_sent_without_recipient(self, mock_mail, app, project, institutional_admin, url,
                                                 create_payload, institution):
        """
        Test that an email is not sent when no recipient is listed when an institutional access request is made,
        but the request is still made anyway without email.
        """
        del create_payload['data']['relationships']['message_recipient']
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        # Check that an email is sent
        assert not mock_mail.called

    @mock.patch('api.requests.serializers.send_mail')
    def test_email_not_sent_outside_institution(self, mock_mail, app, project, institutional_admin, url,
                                                 create_payload, user_without_affiliation, institution):
        """
        Test that you are prevented from requesting a user with the correct institutional affiliation.
        """
        create_payload['data']['relationships']['message_recipient']['data']['id'] = user_without_affiliation._id
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert f'User {user_without_affiliation._id} is not affiliated with the institution.' in res.json['errors'][0]['detail']

        # Check that an email is sent
        assert not mock_mail.called

    @mock.patch('api.requests.serializers.send_mail')
    def test_email_sent_on_creation(
            self,
            mock_mail,
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
        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_mail.call_count == 1

        mock_mail.assert_called_with(
            to_addr=user_with_affiliation.username,
            mail=NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            bcc_addr=None,
            reply_to=None,
            **{
                'sender': institutional_admin,
                'recipient': user_with_affiliation,
                'comment': create_payload['data']['attributes']['comment'],
                'institution': institution,
                'osf_url': mock.ANY,
                'node': project,
            }
        )

    @mock.patch('api.requests.serializers.send_mail')
    def test_bcc_institutional_admin(
            self,
            mock_mail,
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

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_mail.call_count == 1

        mock_mail.assert_called_with(
            to_addr=user_with_affiliation.username,
            mail=NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            bcc_addr=[institutional_admin.username],
            reply_to=None,
            **{
                'sender': institutional_admin,
                'recipient': user_with_affiliation,
                'comment': create_payload['data']['attributes']['comment'],
                'institution': institution,
                'osf_url': mock.ANY,
                'node': project,
            }
        )

    @mock.patch('api.requests.serializers.send_mail')
    def test_reply_to_institutional_admin(
            self,
            mock_mail,
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

        res = app.post_json_api(url, create_payload, auth=institutional_admin.auth)
        assert res.status_code == 201

        assert mock_mail.call_count == 1

        mock_mail.assert_called_with(
            to_addr=user_with_affiliation.username,
            mail=NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST,
            user=user_with_affiliation,
            bcc_addr=None,
            reply_to=institutional_admin.username,
            **{
                'sender': institutional_admin,
                'recipient': user_with_affiliation,
                'comment': create_payload['data']['attributes']['comment'],
                'institution': institution,
                'osf_url': mock.ANY,
                'node': project,
            }
        )
