import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin, PreprintRequestTestMixin

from osf.utils import permissions

@pytest.mark.django_db
@pytest.mark.enable_enqueue
class TestCreateNodeRequestAction(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, node_request):
        return '/{}actions/requests/nodes/'.format(API_BASE)

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


@pytest.mark.django_db
class TestCreatePreprintRequestAction(PreprintRequestTestMixin):
    @pytest.fixture()
    def url(self, pre_request, post_request, none_request):
        return '/{}actions/requests/preprints/'.format(API_BASE)

    def create_payload(self, _id=None, **attrs):
        payload = {
            'data': {
                'attributes': attrs,
                'relationships': {},
                'type': 'preprint-request-actions'
            }
        }
        if _id:
            payload['data']['relationships']['target'] = {
                'data': {
                    'type': 'preprint-requests',
                    'id': _id
                }
            }
        return payload

    def test_no_one_can_view(self, app, admin, write_contrib, noncontrib, moderator, url):
        for user in [admin, write_contrib, noncontrib, moderator]:
            res = app.get(url, auth=user.auth, expect_errors=True)
            assert res.status_code == 405

    def test_nonmoderator_cannot_approve(self, app, admin, write_contrib, noncontrib, url, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            initial_state = request.machine_state
            payload = self.create_payload(request._id, trigger='accept')
            for user in [admin, write_contrib, noncontrib]:
                res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
                assert res.status_code == 403
                request.reload()
                assert initial_state == request.machine_state

    def test_nonmoderator_cannot_reject(self, app, admin, write_contrib, noncontrib, url, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            initial_state = request.machine_state
            payload = self.create_payload(request._id, trigger='reject')
            for user in [admin, write_contrib, noncontrib]:
                res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
                assert res.status_code == 403
                request.reload()
                assert initial_state == request.machine_state

    def test_submitter_can_edit_comment(self, app, admin, url, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            initial_state = request.machine_state
            initial_comment = request.comment
            payload = self.create_payload(request._id, trigger='edit_comment', comment='ASDFG')
            res = app.post_json_api(url, payload, auth=admin.auth)
            assert res.status_code == 201
            request.reload()
            assert initial_state == request.machine_state
            assert initial_comment != request.comment

    def test_moderator_can_approve_moderated_requests(self, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='accept')
            res = app.post_json_api(url, payload, auth=moderator.auth)
            assert res.status_code == 201
            request.reload()
            request.target.reload()
            assert initial_state != request.machine_state
            assert request.target.is_retracted

    def test_moderator_cannot_approve_or_reject_or_edit_comment_nonmoderated_requests(self, app, moderator, url, none_request):
        initial_state = none_request.machine_state
        assert not none_request.target.is_retracted
        payload = self.create_payload(none_request._id, trigger='accept')
        res = app.post_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        none_request.reload()
        assert initial_state == none_request.machine_state
        assert not none_request.target.is_retracted
        payload = self.create_payload(none_request._id, trigger='reject')
        res = app.post_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        none_request.reload()
        assert initial_state == none_request.machine_state
        assert not none_request.target.is_retracted
        initial_comment = none_request.comment
        payload = self.create_payload(none_request._id, trigger='edit_comment', comment='ASDFG')
        res = app.post_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        none_request.reload()
        assert initial_state == none_request.machine_state
        assert initial_comment == none_request.comment
        assert not none_request.target.is_retracted

    def test_moderator_can_reject_moderated_requests(self, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='reject')
            res = app.post_json_api(url, payload, auth=moderator.auth)
            assert res.status_code == 201
            request.reload()
            assert initial_state != request.machine_state
            assert not request.target.is_retracted

    def test_moderator_cannot_edit_comment_moderated_requests(self, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            initial_comment = request.comment
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='edit_comment', comment='ASDFG')
            res = app.post_json_api(url, payload, auth=moderator.auth, expect_errors=True)
            assert res.status_code == 403
            request.reload()
            assert initial_state == request.machine_state
            assert initial_comment == request.comment

    def test_write_contrib_and_noncontrib_cannot_edit_comment(self, app, write_contrib, noncontrib, url, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            for user in [noncontrib, write_contrib]:
                initial_state = request.machine_state
                initial_comment = request.comment
                payload = self.create_payload(request._id, trigger='edit_comment', comment='{}ASDFG'.format(user._id))
                res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
                assert res.status_code == 403
                request.reload()
                assert initial_state == request.machine_state
                assert initial_comment == request.comment

    @mock.patch('website.reviews.listeners.mails.send_mail')
    def test_email_sent_on_approve(self, mock_mail, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='accept')
            res = app.post_json_api(url, payload, auth=moderator.auth)
            assert res.status_code == 201
            request.reload()
            request.target.reload()
            assert initial_state != request.machine_state
            assert request.target.is_retracted
        # There are two preprints withdrawn and each preprint have 2 contributors. So 4 emails are sent in total.
        assert mock_mail.call_count == 4

    @pytest.mark.skip('TODO: IN-331 -- add emails')
    @mock.patch('website.reviews.listeners.mails.send_mail')
    def test_email_sent_on_reject(self, mock_mail, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='reject')
            res = app.post_json_api(url, payload, auth=moderator.auth)
            assert res.status_code == 201
            request.reload()
            assert initial_state != request.machine_state
            assert not request.target.is_retracted
        assert mock_mail.call_count == 2

    @pytest.mark.skip('TODO: IN-284/331 -- add emails')
    @mock.patch('website.reviews.listeners.mails.send_mail')
    def test_email_not_sent_on_edit_comment(self, mock_mail, app, moderator, url, pre_request, post_request):
        for request in [pre_request, post_request]:
            initial_state = request.machine_state
            assert not request.target.is_retracted
            payload = self.create_payload(request._id, trigger='edit_comment', comment='ASDFG')
            res = app.post_json_api(url, payload, auth=moderator.auth)
            assert res.status_code == 201
            request.reload()
            assert initial_state != request.machine_state
            assert not request.target.is_retracted
        assert mock_mail.call_count == 0

    def test_auto_approve(self, app, auto_withdrawable_pre_mod_preprint, auto_approved_pre_request):
        assert auto_withdrawable_pre_mod_preprint.is_retracted
