import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import NodeRequestTestMixin

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
