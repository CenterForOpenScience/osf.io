import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin

from osf_tests.factories import NodeFactory, NodeRequestFactory, InstitutionFactory
from osf.utils.workflows import DefaultStates, NodeRequestTypes


@pytest.mark.django_db
@pytest.mark.usefixtures('mock_send_grid')
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

    def test_email_sent_to_all_admins_on_submit(self, mock_send_grid, app, project, noncontrib, url, create_payload, second_admin):
        project.is_public = True
        project.save()
        mock_send_grid.reset_mock()
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        assert mock_send_grid.call_count == 2

    def test_email_not_sent_to_parent_admins_on_submit(self, mock_send_grid, app, project, noncontrib, url, create_payload, second_admin):
        component = NodeFactory(parent=project, creator=second_admin)
        component.is_public = True
        project.save()
        url = f'/{API_BASE}nodes/{component._id}/requests/'
        mock_send_grid.reset_mock()
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        assert component.parent_admin_contributors.count() == 1
        assert component.contributors.count() == 1
        assert mock_send_grid.call_count == 1

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

    def test_requester_can_make_access_request_after_insti_access_accepted(self, app, project, noncontrib, admin, url, create_payload):
        """
        Test that a requester can submit another access request, then institutional access for the same node.
        """
        create_payload['data']['attributes']['request_type'] = NodeRequestTypes.INSTITUTIONAL_REQUEST.value
        institution = InstitutionFactory(institutional_request_access_enabled=True)
        create_payload['data']['relationships'] = {
            'institution': {
                'data': {
                    'id': institution._id,
                    'type': 'institutions'
                }
            }
        }
        noncontrib.add_or_update_affiliated_institution(institution)
        group = institution.get_group('institutional_admins')
        group.user_set.add(noncontrib)
        group.save()
        # Create the first request a basic request_type == `institutional_request` request
        app.post_json_api(url, create_payload, auth=noncontrib.auth)
        node_request = project.requests.get()
        node_request.run_accept(project.creator, 'test comment2')
        node_request.refresh_from_db()
        assert node_request.machine_state == 'accepted'
        assert node_request.request_type == 'institutional_request'

        project.remove_contributor(noncontrib, auth=noncontrib)
        create_payload['data']['attributes']['request_type'] = NodeRequestTypes.ACCESS.value

        # Attempt to create a second request, refresh and update as institutional
        res = app.post_json_api(url, create_payload, auth=noncontrib.auth)
        assert res.status_code == 201
        node_request.refresh_from_db()
        assert node_request.machine_state == 'accepted'
        assert node_request.request_type == 'institutional_request'
