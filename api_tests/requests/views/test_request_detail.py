import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin, PreprintRequestTestMixin

@pytest.mark.django_db
class TestNodeRequestDetail(NodeRequestTestMixin):
    @pytest.fixture()
    def url(self, node_request):
        return '/{}requests/{}/'.format(API_BASE, node_request._id)

    def test_admin_can_view_request(self, app, url, admin):
        res = app.get(url, auth=admin.auth)
        assert res.status_code == 200

    def test_requester_can_view_request(self, app, url, requester):
        res = app.get(url, auth=requester.auth)
        assert res.status_code == 200

    def test_write_contrib_cannot_view_request(self, app, url, write_contrib):
        res = app.get(url, auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_noncontrib_cannot_view_request(self, app, url, noncontrib):
        res = app.get(url, auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

@pytest.mark.django_db
class TestPreprintRequestDetail(PreprintRequestTestMixin):
    def url(self, request):
        return '/{}requests/{}/'.format(API_BASE, request._id)

    def test_admin_can_view_request(self, app, admin, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            url = self.url(request)
            res = app.get(url, auth=admin.auth)
            assert res.status_code == 200

    def test_moderator_view_permissions(self, app, moderator, pre_request, post_request, none_request):
        for request in [pre_request, post_request]:
            url = self.url(request)
            res = app.get(url, auth=moderator.auth)
            assert res.status_code == 200
        url = self.url(none_request)
        res = app.get(url, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_noncontrib_cannot_view_request(self, app, noncontrib, write_contrib, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            for user in [noncontrib, write_contrib]:
                url = self.url(request)
                res = app.get(url, auth=user.auth, expect_errors=True)
                assert res.status_code == 403
                assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'
