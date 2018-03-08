import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin

from osf.utils import permissions

@pytest.mark.django_db
class TestCreateNodeRequestAction(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, node_request):
        return '/{}actions/requests/'.format(API_BASE)

    def create_payload(self, _id=None, **attrs):
        payload = {
            'data': {
                'attributes': attrs,
                'relationships': {},
                'type': 'node-request-actions'
            }
        }
        if _id:
            payload['data']['relationships']['target'] = {
                'data': {
                    'type': 'node-requests',
                    'id': _id
                }
            }
        return payload

    def test_requester_cannot_view(self, app, requester, url):
        res = app.get(url, auth=requester.auth, expect_errors=True)
        assert res.status_code == 405

    def test_requester_cannot_approve(self, app, requester, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=requester.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_requester_cannot_reject(self, app, requester, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=requester.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_requester_can_edit_comment(self, app, requester, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=requester.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment != node_request.comment

    def test_admin_can_approve(self, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state != node_request.machine_state
        assert node_request.creator in node_request.target.contributors

    def test_admin_can_reject(self, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state != node_request.machine_state
        assert node_request.creator not in node_request.target.contributors

    def test_admin_cannot_view(self, app, admin, url):
        res = app.get(url, auth=admin.auth, expect_errors=True)
        assert res.status_code == 405

    def test_admin_cannot_edit_comment(self, app, admin, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment == node_request.comment

    def test_write_contrib_cannot_approve(self, app, write_contrib, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_write_contrib_cannot_reject(self, app, write_contrib, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_write_contrib_cannot_view(self, app, write_contrib, url):
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 405

    def test_write_contrib_cannot_edit_comment(self, app, write_contrib, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment == node_request.comment

    def test_noncontrib_cannot_approve(self, app, noncontrib, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_noncontrib_cannot_reject(self, app, noncontrib, url, node_request):
        initial_state = node_request.machine_state
        payload = self.create_payload(node_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state

    def test_noncontrib_cannot_view(self, app, noncontrib, url):
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 405

    def test_noncontrib_cannot_edit_comment(self, app, noncontrib, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment == node_request.comment

    def test_edits_fail_with_requests_disabled(self, app, requester, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        node_request.target.access_requests_enabled = False
        node_request.target.save()
        res = app.post_json_api(url, payload, auth=requester.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment == node_request.comment

    def test_approves_fail_with_requests_disabled(self, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept')
        node_request.target.access_requests_enabled = False
        node_request.target.save()
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert node_request.creator not in node_request.target.contributors

    def test_rejects_fail_with_requests_disabled(self, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='reject')
        node_request.target.access_requests_enabled = False
        node_request.target.save()
        res = app.post_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 403
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert node_request.creator not in node_request.target.contributors

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_email_sent_on_approve(self, mock_mail, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state != node_request.machine_state
        assert node_request.creator in node_request.target.contributors
        assert mock_mail.call_count == 1

    @mock.patch('website.mails.mails.send_mail')
    def test_email_sent_on_reject(self, mock_mail, app, admin, url, node_request):
        initial_state = node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state != node_request.machine_state
        assert node_request.creator not in node_request.target.contributors
        assert mock_mail.call_count == 1

    @mock.patch('website.mails.mails.send_mail')
    def test_email_not_sent_on_reject(self, mock_mail, app, requester, url, node_request):
        initial_state = node_request.machine_state
        initial_comment = node_request.comment
        payload = self.create_payload(node_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=requester.auth)
        assert res.status_code == 201
        node_request.reload()
        assert initial_state == node_request.machine_state
        assert initial_comment != node_request.comment
        assert mock_mail.call_count == 0

    def test_set_permissions_on_approve(self, app, admin, url, node_request):
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept', permissions='admin')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert node_request.target.has_permission(node_request.creator, permissions.ADMIN)

    def test_set_visible_on_approve(self, app, admin, url, node_request):
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept', visible=False)
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert node_request.creator in node_request.target.contributors
        assert not node_request.target.get_visible(node_request.creator)

    def test_accept_request_defaults_to_read_and_visible(self, app, admin, url, node_request):
        assert node_request.creator not in node_request.target.contributors
        payload = self.create_payload(node_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 201
        node_request.reload()
        assert node_request.creator in node_request.target.contributors
        assert node_request.target.has_permission(node_request.creator, permissions.READ)
        assert node_request.target.get_visible(node_request.creator)
