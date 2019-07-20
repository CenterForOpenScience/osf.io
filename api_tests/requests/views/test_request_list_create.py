import mock
import pytest

from osf.utils import workflows
from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin, PreprintRequestTestMixin
from osf_tests.factories import NodeFactory, NodeRequestFactory

@pytest.mark.django_db
class TestNodeRequestListCreate(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, project):
        return '/{}nodes/{}/requests/'.format(API_BASE, project._id)

    @pytest.fixture()
    def create_payload(self):
        return {
            'data': {
                'attributes': {
                    'comment': 'ASDFG',
                    'request_type': 'access'
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
        url = '/{}nodes/{}/requests/'.format(API_BASE, component._id)
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
            request_type=workflows.RequestTypes.ACCESS.value,
            machine_state=workflows.DefaultStates.INITIAL.value
        )
        filtered_url = '{}?filter[machine_state]=pending'.format(url)
        res = app.get(filtered_url, auth=admin.auth)
        assert res.status_code == 200
        ids = [result['id'] for result in res.json['data']]
        assert initial_node_request._id not in ids
        assert node_request.machine_state == 'pending' and node_request._id in ids

@pytest.mark.django_db
class TestPreprintRequestListCreate(PreprintRequestTestMixin):
    def url(self, preprint):
        return '/{}preprints/{}/requests/'.format(API_BASE, preprint._id)

    @pytest.fixture()
    def create_payload(self):
        return {
            'data': {
                'attributes': {
                    'comment': 'ASDFG',
                    'request_type': 'withdrawal'
                },
                'type': 'preprint-requests'
            }
        }

    def test_noncontrib_cannot_submit(self, app, noncontrib, create_payload, pre_mod_preprint, post_mod_preprint, none_mod_preprint):
        for preprint in [pre_mod_preprint, post_mod_preprint, none_mod_preprint]:
            res = app.post_json_api(self.url(preprint), create_payload, auth=noncontrib.auth, expect_errors=True)
            assert res.status_code == 403

    def test_unauth_cannot_submit(self, app, create_payload, pre_mod_preprint, post_mod_preprint, none_mod_preprint):
        for preprint in [pre_mod_preprint, post_mod_preprint, none_mod_preprint]:
            res = app.post_json_api(self.url(preprint), create_payload, expect_errors=True)
            assert res.status_code == 401

    def test_write_contributor_cannot_submit(self, app, write_contrib, create_payload, pre_mod_preprint, post_mod_preprint, none_mod_preprint):
        for preprint in [pre_mod_preprint, post_mod_preprint, none_mod_preprint]:
            res = app.post_json_api(self.url(preprint), create_payload, auth=write_contrib.auth, expect_errors=True)
            assert res.status_code == 403

    def test_admin_can_submit(self, app, admin, create_payload, pre_mod_preprint, post_mod_preprint, none_mod_preprint):
        for preprint in [pre_mod_preprint, post_mod_preprint, none_mod_preprint]:
            res = app.post_json_api(self.url(preprint), create_payload, auth=admin.auth)
            assert res.status_code == 201

    def test_admin_can_view_requests(self, app, admin, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            res = app.get(self.url(request.target), auth=admin.auth)
            assert res.status_code == 200
            assert res.json['data'][0]['id'] == request._id

    def test_noncontrib_and_write_contrib_cannot_view_requests(self, app, noncontrib, write_contrib, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            for user in [noncontrib, write_contrib]:
                res = app.get(self.url(request.target), auth=user.auth, expect_errors=True)
                assert res.status_code == 403

    def test_unauth_cannot_view_requests(self, app, noncontrib, write_contrib, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            res = app.get(self.url(request.target), expect_errors=True)
            assert res.status_code == 401

    def test_requester_cannot_submit_again(self, app, admin, create_payload, pre_mod_preprint, pre_request):
        res = app.post_json_api(self.url(pre_mod_preprint), create_payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Users may not have more than one withdrawal request per preprint.'

    @pytest.mark.skip('TODO: IN-284 -- add emails')
    @mock.patch('website.reviews.listeners.mails.send_mail')
    def test_email_sent_to_moderators_on_submit(self, mock_mail, app, admin, create_payload, moderator, post_mod_preprint):
        res = app.post_json_api(self.url(post_mod_preprint), create_payload, auth=admin.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1
