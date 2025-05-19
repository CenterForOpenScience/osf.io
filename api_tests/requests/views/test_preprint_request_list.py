from unittest import mock
import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import PreprintRequestTestMixin


@pytest.mark.django_db
class TestPreprintRequestListCreate(PreprintRequestTestMixin):
    def url(self, preprint):
        return f'/{API_BASE}preprints/{preprint._id}/requests/'

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
    @mock.patch('website.reviews.listeners.mails.execute_email_send')
    def test_email_sent_to_moderators_on_submit(self, mock_mail, app, admin, create_payload, moderator, post_mod_preprint):
        res = app.post_json_api(self.url(post_mod_preprint), create_payload, auth=admin.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1
