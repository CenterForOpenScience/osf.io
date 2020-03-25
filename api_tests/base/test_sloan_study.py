import pytest
from api_tests.utils import retry_assertion

from waffle.models import Flag

from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory
)

from osf.features import (
    SLOAN_COI_DISPLAY,
    SLOAN_DATA_DISPLAY,
    SLOAN_PREREG_DISPLAY,
)

SLOAN_FLAGS = (
    SLOAN_COI_DISPLAY,
    SLOAN_DATA_DISPLAY,
    SLOAN_PREREG_DISPLAY
)

from osf.system_tags import (
    SLOAN_COI,
    SLOAN_PREREG,
    SLOAN_DATA,
)

from website.settings import DOMAIN
from api.base.views import get_provider_from_url


@pytest.mark.django_db
class TestSloanStudyWaffling:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user):
        return PreprintFactory(creator=user)

    @pytest.fixture(autouse=True)
    def providers(self, user):
        PreprintProviderFactory(_id='foorxiv').save()
        PreprintProviderFactory(_id='osf').save()

    @pytest.fixture(autouse=True)
    def flags(self, user):
        Flag.objects.filter(name__in=SLOAN_FLAGS, percent=50).update(everyone=None)

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_sloan_study_variable(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=99)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_COI in tags
        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_sloan_study_control(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=1)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert f'no_{SLOAN_COI}' in tags
        assert f'no_{SLOAN_DATA}' in tags
        assert f'no_{SLOAN_PREREG}' in tags

        assert SLOAN_COI_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    def test_sloan_study_variable_unauth(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=99)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    def test_sloan_study_control_unauth(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=1)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_COI_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies

    @pytest.mark.parametrize('reffer_url, expected_provider_id', [
        (f'{DOMAIN}preprints', 'osf'),
        (f'{DOMAIN}preprints/', 'osf'),
        (f'{DOMAIN}preprints/not/a/valid/path/', 'osf'),
        (f'{DOMAIN}preprints/foorxiv', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/aguid', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/aguid/', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/foo/bar/baz/', 'foorxiv')
    ])
    def test_weird_domains(self, reffer_url, expected_provider_id):
        provider = get_provider_from_url(reffer_url)
        assert expected_provider_id == provider._id

    @pytest.mark.parametrize('reffer_url', [
        DOMAIN,
        f'{DOMAIN}not-preprints/',
    ])
    def test_too_weird_domains(self, reffer_url):
        provider = get_provider_from_url(reffer_url)
        assert provider is None

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_provider_custom_domain(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=99)

        provider = preprint.provider
        provider.domain = 'https://burdixiv.burds/'
        provider.save()
        headers = {'Referer': f'https://burdixiv.burds/preprints/{preprint._id}'}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_COI in tags
        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_unauth_user_logs_in(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=99)

        user.add_system_tag(SLOAN_COI)
        user.add_system_tag(SLOAN_PREREG)

        cookies = {
            SLOAN_COI_DISPLAY: 'False',
            SLOAN_DATA_DISPLAY: 'True',
        }

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers, cookies=cookies)

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_user_get_cookie_when_flag_is_everyone(self, app, user, preprint):
        user.add_system_tag(f'no_{SLOAN_PREREG}')
        Flag.objects.filter(name=SLOAN_COI_DISPLAY).update(everyone=True)
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        cookies = resp.headers.getall('Set-Cookie')
        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; Secure' in cookies

    @retry_assertion()
    @pytest.mark.enable_quickfiles_creation
    def test_sloan_study_non_localhost(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=99)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers, extra_environ={'SERVER_NAME': 'osf.io'})

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_COI in tags
        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=.osf.io; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=.osf.io; Path=/; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=.osf.io; Path=/; Secure' in cookies
