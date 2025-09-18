import pytest
from osf_tests.factories import (
    NodeRequestFactory,
    AuthUserFactory,
    NodeFactory,
    InstitutionFactory
)
from api.base.settings.defaults import API_BASE
from osf.utils.workflows import NodeRequestTypes

@pytest.mark.django_db
class TestUniqueIndexOnNodeRequest:

    @pytest.fixture()
    def url(self, project):
        return f'/{API_BASE}nodes/{project._id}/requests/'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user_with_affiliation, institution):
        node = NodeFactory()
        node.add_affiliated_institution(institution, user_with_affiliation)
        return node

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory(institutional_request_access_enabled=True)

    @pytest.fixture()
    def user_with_affiliation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        institution.get_group('institutional_admins').user_set.add(user)
        return user

    @pytest.fixture()
    def create_payload(self, project, institution):
        return {
            'data': {
                'attributes': {
                    'comment': 'Testing unique index',
                    'request_type': NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
                },
                'relationships': {
                    'institution': {
                        'data': {
                            'id': institution._id,
                            'type': 'institutions'
                        }
                    },
                },
                'type': 'node-requests'
            }
        }

    def test_multiple_node_requests_error(self, app, project, user, user_with_affiliation, url, create_payload):
        """
        Ensure that multiple NodeRequest objects for the same user and target raise an error.
        """
        NodeRequestFactory(
            target=project,
            creator=user_with_affiliation,
            request_type=NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
            machine_state='accepted',
        )
        NodeRequestFactory(
            target=project,
            creator=user_with_affiliation,
            request_type=NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
            machine_state='accepted',
        )

        res = app.post_json_api(
            url,
            create_payload,
            auth=user_with_affiliation.auth,
        )
        assert res.status_code == 201
