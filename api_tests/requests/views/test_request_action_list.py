import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import PreprintRequestTestMixin

@pytest.mark.django_db
class TestPreprintRequestActionList(PreprintRequestTestMixin):
    def url(self, request):
        return '/{}requests/{}/actions/'.format(API_BASE, request._id)

    def test_nonmod_cannot_view(self, app, noncontrib, write_contrib, admin, pre_request, post_request, none_request):
        for request in [pre_request, post_request, none_request]:
            for user in [noncontrib, write_contrib, admin]:
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
