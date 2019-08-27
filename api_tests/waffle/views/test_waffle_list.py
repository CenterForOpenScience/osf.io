import pytest

from waffle.models import Flag, Switch, Sample

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    FlagFactory,
    SampleFactory,
    SwitchFactory
)
from api.base.pagination import MaxSizePagination

@pytest.mark.django_db
class TestWaffleList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def inactive_flag(self):
        return FlagFactory(name='inactive_flag', everyone=False)

    @pytest.fixture()
    def active_flag(self):
        return FlagFactory(name='active_flag')

    @pytest.fixture()
    def inactive_switch(self):
        return SwitchFactory(name='inactive_switch', active=False)

    @pytest.fixture()
    def active_sample(self):
        return SampleFactory(name='active_sample')

    @pytest.fixture()
    def url(self):
        return '/{}_waffle/'.format(API_BASE)

    @pytest.fixture()
    def flag_url(self, url):
        return url + '?flags=active_flag'

    def test_waffle_flag_no_filter(self, app, user, url, inactive_flag, active_flag):
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == Flag.objects.all().count() + Switch.objects.all().count() + Sample.objects.all().count()

    def test_waffle_flag_filter_active(self, app, user, flag_url, active_flag):
        res = app.get(flag_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['name'] == 'active_flag'
        assert res.json['data'][0]['attributes']['active'] is True

    def test_waffle_flag_filter_does_not_exist(self, app, user, url, inactive_flag, active_flag):
        res = app.get(url + '?flags=jibberish', auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

    def test_filter_waffle_samples_flags_and_switches(self, app, user, url, inactive_flag, active_flag, active_sample, inactive_switch):
        res = app.get(url + '?flags=active_flag&samples=active_sample&switches=inactive_switch', auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 3

    def test_waffle_switch_logged_out(self, app, user, url, inactive_switch):
        res = app.get(url + '?switches=inactive_switch')
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['name'] == 'inactive_switch'
        assert not res.json['data'][0]['attributes']['active']

    def test_page_size(self, app, url, user):
        res = app.get(url)
        assert res.json['links']['meta']['per_page'] == MaxSizePagination.page_size
