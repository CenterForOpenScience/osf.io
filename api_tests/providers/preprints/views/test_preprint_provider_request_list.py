import pytest

from api.base.settings.defaults import API_BASE
from api_tests.requests.mixins import PreprintRequestTestMixin

@pytest.mark.django_db
class TestPreprintProviderWithdrawalRequstList(PreprintRequestTestMixin):
    def url(self, provider):
        return '/{}providers/preprints/{}/withdraw_requests/'.format(API_BASE, provider._id)

    def test_list(self, app, admin, moderator, write_contrib, noncontrib, pre_mod_provider, post_mod_provider, pre_mod_preprint, post_mod_preprint, pre_request, post_request):
        # test_no_perms
        res = app.get(self.url(pre_mod_provider), auth=admin.auth, expect_errors=True)  # preprint admin, not reviews admin
        assert res.status_code == 403
        res = app.get(self.url(pre_mod_provider), auth=write_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.get(self.url(pre_mod_provider), auth=noncontrib.auth, expect_errors=True)
        assert res.status_code == 403
        res = app.get(self.url(pre_mod_provider), expect_errors=True)
        assert res.status_code == 401

        # test_moderator_can_view
        res = app.get(self.url(pre_mod_provider), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == pre_request._id

        res = app.get(self.url(post_mod_provider), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == post_request._id

        # test_embed
        res = app.get('{}?embed=target'.format(self.url(pre_mod_provider)), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == pre_request._id
        assert res.json['data'][0]['embeds']['target']['data']['id'] == pre_mod_preprint._id

        res = app.get('{}?embed=target'.format(self.url(post_mod_provider)), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == post_request._id
        assert res.json['data'][0]['embeds']['target']['data']['id'] == post_mod_preprint._id

        # test_filter
        res = app.get('{}?filter[target]={}'.format(self.url(pre_mod_provider), pre_mod_preprint._id), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == pre_request._id

        res = app.get('{}?filter[target]={}'.format(self.url(post_mod_provider), post_mod_preprint._id), auth=moderator.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == post_request._id
