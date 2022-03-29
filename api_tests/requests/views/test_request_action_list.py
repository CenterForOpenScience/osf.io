import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import PreprintRequestTestMixin

@pytest.mark.django_db
class TestPreprintRequestActionList(PreprintRequestTestMixin):
    def url(self, request):
        return '/{}requests/{}/actions/'.format(API_BASE, request._id)

    def test_nonmod_nonadmin_nonrequester_cannot_view(self, app, noncontrib, write_contrib, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            for user in [noncontrib, write_contrib]:
                res = app.get(self.url(request), auth=user.auth, expect_errors=True)
                assert res.status_code == 403

    def test_mod_can_view(self, app, moderator, pre_request, post_request, auto_approved_pre_request):
        for request in [pre_request, post_request]:
            res = app.get(self.url(request), auth=moderator.auth)
            assert res.status_code == 200
            assert len(res.json['data']) == 1
            assert res.json['data'][0]['attributes']['auto'] is False
        res = app.get(self.url(auto_approved_pre_request), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['attributes']['auto'] is True

    def test_admin_can_view(self, app, admin, pre_request, post_request, none_request, auto_approved_pre_request):
        for request in [pre_request, post_request, none_request]:
            res = app.get(self.url(request), auth=admin.auth)
            assert res.status_code == 200
            assert len(res.json['data']) == 1
            assert res.json['data'][0]['attributes']['auto'] is False
        res = app.get(self.url(auto_approved_pre_request), auth=admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['attributes']['auto'] is True

    def test_nonadmin_requester_can_view(self, app, requester, nonadmin_pre_request, nonadmin_post_request, nonadmin_none_request, nonadmin_auto_approved_pre_request):
        for request in [nonadmin_pre_request, nonadmin_post_request, nonadmin_none_request]:
            res = app.get(self.url(request), auth=requester.auth)
            assert res.status_code == 200
            assert len(res.json['data']) == 1
            assert res.json['data'][0]['attributes']['auto'] is False
        res = app.get(self.url(nonadmin_auto_approved_pre_request), auth=requester.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['attributes']['auto'] is True
