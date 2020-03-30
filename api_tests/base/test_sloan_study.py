import mock
import pytest
from decimal import Decimal

from waffle.models import Flag
from website.settings import DOMAIN
from api.base.middleware import SloanOverrideWaffleMiddleware
from django.test.utils import override_settings

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


def active(*args, **kwargs):
    return Decimal('0')


def inactive(*args, **kwargs):
    return Decimal('100')


@pytest.mark.django_db
class TestSloanStudyWaffling:
    """
    DEV_MODE is mocked so cookies they behave as if they were using https.
    """

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

    @override_settings(DEV_MODE=False)
    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', active)
    def test_sloan_study_variable(self, app, user, preprint):

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

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies

    @override_settings(DEV_MODE=False)
    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', inactive)
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

        assert f' dwf_{SLOAN_COI_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies

    @override_settings(DEV_MODE=False)
    @mock.patch('waffle.models.Decimal', active)
    def test_sloan_study_variable_unauth(self, app, user, preprint):
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies

    @override_settings(DEV_MODE=False)
    @mock.patch('waffle.models.Decimal', inactive)
    def test_sloan_study_control_unauth(self, app, user, preprint):
        Flag.objects.filter(name__in=SLOAN_FLAGS).update(percent=1)

        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', headers=headers)

        assert SLOAN_COI_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_DATA_DISPLAY not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG_DISPLAY not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies

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
        provider = SloanOverrideWaffleMiddleware.get_provider_from_url(reffer_url)
        assert expected_provider_id == provider._id

    @pytest.mark.parametrize('reffer_url', [
        DOMAIN,
        f'{DOMAIN}not-preprints/',
    ])
    def test_too_weird_domains(self, reffer_url):
        provider = SloanOverrideWaffleMiddleware.get_provider_from_url(reffer_url)
        assert provider is None

    @override_settings(DEV_MODE=False)
    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', active)
    def test_provider_custom_domain(self, app, user, preprint):
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

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=.burdixiv.burds; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_DATA_DISPLAY}=True; Domain=.burdixiv.burds; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=.burdixiv.burds; Path=/; samesite=None; Secure' in cookies

    @override_settings(DEV_MODE=False)
    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', active)
    def test_unauth_user_logs_in(self, app, user, preprint):
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

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies

    @override_settings(DEV_MODE=False)
    @pytest.mark.enable_quickfiles_creation
    def test_user_get_cookie_when_flag_is_everyone(self, app, user, preprint):
        user.add_system_tag(f'no_{SLOAN_PREREG}')
        Flag.objects.filter(name=SLOAN_COI_DISPLAY).update(everyone=True)
        headers = {'Referer': preprint.absolute_url}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        cookies = resp.headers.getall('Set-Cookie')
        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=localhost; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_PREREG_DISPLAY}=False; Domain=localhost; Path=/; samesite=None; Secure' in cookies

    @pytest.mark.parametrize('url, expected_domain', [
        ('https://osf.io/preprints/sdadadsad', '.osf.io'),
        ('https://agrixiv.org/bhzjs/', '.agrixiv.org'),
        ('https://staging-agrixiv.cos.io/', '.staging-agrixiv.cos.io'),
        ('https://staging.osf.io/preprints/', '.staging.osf.io'),
    ])
    def test_get_domain(self, url, expected_domain):
        actual_domain = SloanOverrideWaffleMiddleware.get_domain(url)
        assert actual_domain == expected_domain
