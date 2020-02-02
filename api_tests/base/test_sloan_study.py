import pytest
import mock

from waffle.models import Flag

from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory
)

from osf.features import (
    SLOAN_DATA,
    SLOAN_PREREG,
    SLOAN_COI
)

SLOAN_FLAGS = (
    SLOAN_DATA,
    SLOAN_PREREG,
    SLOAN_COI
)

from website.settings import DOMAIN

@pytest.mark.django_db
class TestSloanStudyWaffling:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture(autouse=True)
    def flags(self, user):
        Flag.objects.filter(name__in=SLOAN_FLAGS, percent=50).update(everyone=None)

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('api.base.views.Flag.is_active')
    def test_sloan_study_variable(self, mock_flag_is_active, app, user, preprint):
        mock_flag_is_active.return_value = True
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags
        assert SLOAN_COI in tags

        assert SLOAN_DATA in resp.json['meta']['active_flags']
        assert SLOAN_PREREG in resp.json['meta']['active_flags']
        assert SLOAN_COI in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=True; Path=/' in cookies
        assert f' {SLOAN_PREREG}=True; Path=/' in cookies
        assert f' {SLOAN_COI}=True; Path=/' in cookies

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('api.base.views.Flag.is_active')
    def test_sloan_study_variable_unauth(self, mock_flag_is_active, app, user, preprint):
        mock_flag_is_active.return_value = True
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_DATA in resp.json['meta']['active_flags']
        assert SLOAN_PREREG in resp.json['meta']['active_flags']
        assert SLOAN_COI in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=True; Path=/' in cookies
        assert f' {SLOAN_PREREG}=True; Path=/' in cookies
        assert f' {SLOAN_COI}=True; Path=/' in cookies

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('api.base.views.Flag.is_active')
    def test_sloan_study_control(self, mock_flag_is_active, app, user, preprint):
        mock_flag_is_active.return_value = False
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert f'no_{SLOAN_DATA}' in tags
        assert f'no_{SLOAN_PREREG}' in tags
        assert f'no_{SLOAN_COI}' in tags

        assert SLOAN_DATA not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG not in resp.json['meta']['active_flags']
        assert SLOAN_COI not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=False; Path=/' in cookies
        assert f' {SLOAN_PREREG}=False; Path=/' in cookies
        assert f' {SLOAN_COI}=False; Path=/' in cookies

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('api.base.views.Flag.is_active')
    def test_sloan_study_control_unauth(self, mock_flag_is_active, app, user, preprint):
        mock_flag_is_active.return_value = False
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_DATA not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG not in resp.json['meta']['active_flags']
        assert SLOAN_COI not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=False; Path=/' in cookies
        assert f' {SLOAN_PREREG}=False; Path=/' in cookies
        assert f' {SLOAN_COI}=False; Path=/' in cookies

    def test_domain_preprint_path(self, app, user, preprint):
        headers = {'Referer': f'{DOMAIN}preprints/'}
        resp = app.get('/v2/', headers=headers)
        resp.status_code == 200

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('api.base.views.Flag.is_active')
    def test_provider_custom_domain(self, mock_flag_is_active, app, user, preprint):
        provider = preprint.provider
        provider.domain = 'https://burdixiv.burds/'
        provider.save()
        mock_flag_is_active.return_value = True
        headers = {'Referer': f'https://burdixiv.burds/preprints/{preprint._id}'}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags
        assert SLOAN_COI in tags

        assert SLOAN_DATA in resp.json['meta']['active_flags']
        assert SLOAN_PREREG in resp.json['meta']['active_flags']
        assert SLOAN_COI in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=True; Path=/' in cookies
        assert f' {SLOAN_PREREG}=True; Path=/' in cookies
        assert f' {SLOAN_COI}=True; Path=/' in cookies

    @pytest.mark.enable_quickfiles_creation
    def test_unauth_user_logs_in(self, app, user, preprint):
        user.add_system_tag(SLOAN_COI)
        user.add_system_tag(SLOAN_PREREG)

        cookies = {
            SLOAN_COI: 'False',
            SLOAN_DATA: 'True',
        }

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers, cookies=cookies)

        assert SLOAN_COI in resp.json['meta']['active_flags']
        assert SLOAN_PREREG in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_COI}=True; Path=/' in cookies
        assert f' {SLOAN_PREREG}=True; Path=/' in cookies
