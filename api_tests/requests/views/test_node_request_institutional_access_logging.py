import pytest

from api.base.settings.defaults import API_BASE

from osf_tests.factories import NodeFactory, InstitutionFactory, AuthUserFactory
from osf.models import NodeLog, NodeRequest
from osf.utils.workflows import NodeRequestTypes

@pytest.mark.django_db
class TestNodeRequestListInstitutionalAccessActionAccept:

    @pytest.fixture
    def action_payload(self, node_request):
        return {
            'data': {
                'attributes': {
                    'trigger': 'accept',
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'node-requests',
                            'id': node_request._id,
                        }
                    }
                },
                'type': 'node-request-actions'
            }
        }

    @pytest.fixture()
    def url(self, project):
        return f'/{API_BASE}actions/requests/nodes/'

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory(institutional_request_access_enabled=True)

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
    def project(self, institutional_admin, user_with_affiliation):
        node = NodeFactory(creator=user_with_affiliation)
        return node

    @pytest.fixture()
    def node_request(self, institutional_admin, user_with_affiliation, project):
        return NodeRequest.objects.create(
            target=project,
            creator=institutional_admin,
            comment='test comment',
            request_type=NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
            machine_state='pending'
        )

    def test_post_node_request_action_success_logged_as_curator(self, app, action_payload, url, user_with_affiliation, institutional_admin, project):
        """
        Test a successful POST request to create a node-request action and log it.
        """
        # Perform the POST request
        res = app.post_json_api(url, action_payload, auth=user_with_affiliation.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['trigger'] == 'accept'

        # Fetch the log entry
        log = project.logs.get(action=NodeLog.CURATOR_ADDED)

        # Assert log details
        assert log.action == NodeLog.CURATOR_ADDED
        assert log.user_id == user_with_affiliation.id
        assert log.node_id == project.id
        assert log.params['node'] == project._id
        assert 'contributors' in log.params
        assert institutional_admin._id in log.params['contributors']

    def test_post_node_request_action_reject_curator(self, app, action_payload, url, user_with_affiliation, institutional_admin, project):
        """
        Test a successful POST request to remove a curator and log the action.
        """
        # Perform the POST request
        action_payload['data']['attributes']['trigger'] = 'reject'
        res = app.post_json_api(url, action_payload, auth=user_with_affiliation.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['trigger'] == 'reject'

        assert not project.contributors.filter(id=institutional_admin.id).exists()
        assert not project.logs.filter(action=NodeLog.CURATOR_ADDED)
