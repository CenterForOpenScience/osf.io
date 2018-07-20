import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin, PreprintRequestTestMixin


@pytest.mark.django_db
class TestActionDetailNodeRequests(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, node_request):
        action = node_request.actions.last()
        return '/{}actions/{}/'.format(API_BASE, action._id)

    def test_admin_cannot_view_action(self, app, url, admin):
        res = app.get(url, auth=admin.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to view this Action'

    def test_requester_cannot_view_action(self, app, url, requester):
        res = app.get(url, auth=requester.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to view this Action'

    def test_write_contrib_cannot_view_action(self, app, url, write_contrib):
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to view this Action'

    def test_noncontrib_cannot_view_action(self, app, url, noncontrib):
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to view this Action'

@pytest.mark.django_db
class TestActionDetailPreprintRequests(PreprintRequestTestMixin):
    def url(self, request):
        action = request.actions.last()
        return '/{}actions/{}/'.format(API_BASE, action._id)

    def test_no_one_can_view_these_actions(self, app, admin, write_contrib, noncontrib, moderator, pre_request, post_request, none_request):
        pre_url = self.url(pre_request)
        post_url = self.url(post_request)
        none_url = self.url(none_request)

        for url in [pre_url, post_url, none_url]:
            for user in [admin, write_contrib, noncontrib, moderator]:
                res = app.get(url, auth=user.auth, expect_errors=True)
                assert res.status_code == 403
                assert res.json['errors'][0]['detail'] == 'You do not have permission to view this Action'
