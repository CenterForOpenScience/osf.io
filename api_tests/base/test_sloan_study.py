import mock
import pytest
from decimal import Decimal

from waffle.models import Flag
from website.settings import DOMAIN
from api.base.middleware import SloanOverrideWaffleMiddleware

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

    @pytest.fixture()
    def preprint_with_guid(self):
        preprint_with_guid = PreprintFactory()
        preprint_with_guid.provider._id = 'test id'
        preprint_with_guid.provider.save()
        guid = preprint_with_guid.guids.last()
        guid._id = 'ispp0'
        guid.save()

        return preprint_with_guid

    @pytest.fixture(autouse=True)
    def providers(self, user):
        PreprintProviderFactory(_id='foorxiv').save()
        PreprintProviderFactory(_id='osf').save()
        PreprintProviderFactory(_id='burdixiv', domain='https://burdixiv.burds/', domain_redirect_enabled=True).save()
        PreprintProviderFactory(_id='shady', domain='https://staging2.osf.io/', domain_redirect_enabled=False).save()

    @pytest.fixture(autouse=True)
    def flags(self, user):
        Flag.objects.filter(name__in=SLOAN_FLAGS, percent=50).update(everyone=None)

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

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', inactive)
    def test_sloan_study_control(self, app, user, preprint):
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

    @mock.patch('waffle.models.Decimal', inactive)
    def test_sloan_study_control_unauth(self, app, user, preprint):
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
        (f'https://staging2.osf.io/', None),
        (f'https://staging2.osf.io/ispp0/', 'test id'),
        (f'https://burdixiv.burds/', 'burdixiv'),
        (f'https://burdixiv.burds/guid0', 'burdixiv'),
        (f'https://burdixiv.burds/guid0', 'burdixiv'),
        (f'https://staging2.osf.io/', None),
        (f'{DOMAIN}preprints', 'osf'),
        (f'{DOMAIN}preprints/', 'osf'),
        (f'{DOMAIN}preprints/not/a/valid/path/', 'osf'),
        (f'{DOMAIN}preprints/foorxiv', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/aguid', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/aguid/', 'foorxiv'),
        (f'{DOMAIN}preprints/foorxiv/foo/bar/baz/', 'foorxiv')

    ])
    def test_weird_domains(self, reffer_url, expected_provider_id, preprint_with_guid):

        provider = SloanOverrideWaffleMiddleware.get_provider_from_url(reffer_url)
        assert expected_provider_id == getattr(provider, '_id', None)

    @pytest.mark.parametrize('reffer_url', [
        DOMAIN,
        f'{DOMAIN}not-preprints/',
    ])
    def test_too_weird_domains(self, reffer_url):
        provider = SloanOverrideWaffleMiddleware.get_provider_from_url(reffer_url)
        assert provider is None

    @pytest.mark.enable_quickfiles_creation
    @mock.patch('waffle.models.Decimal', active)
    def test_provider_custom_domain(self, app, user, preprint):
        headers = {'Referer': f'https://burdixiv.burds/preprints/{preprint._id}'}
        resp = app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_COI in tags

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=.osf.io; Path=/; samesite=None; Secure' in cookies
        assert f' dwf_{SLOAN_COI_DISPLAY}_custom_domain=True; Domain=.burdixiv.burds; Path=/; samesite=None; Secure' in cookies

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
        ('https://agrixiv.org/bhzjs/', '.osf.io'),
        ('https://staging-agrixiv.cos.io/', '.staging.osf.io'),
        ('https://staging.osf.io/preprints/', '.staging.osf.io'),
        ('https://staging2.osf.io/preprints/', '.staging2.osf.io'),
        ('https://staging3.osf.io/preprints/', '.staging3.osf.io'),
        ('https://test.osf.io/preprints/', '.test.osf.io'),
        ('https://staging2-engrxiv.cos.io/', '.staging2.osf.io'),
    ])
    def test_get_domain(self, url, expected_domain):
        actual_domain = SloanOverrideWaffleMiddleware.get_domain(url)
        assert actual_domain == expected_domain

    @pytest.mark.enable_quickfiles_creation
    def test_user_override_cookie(self, app, user, preprint):
        user.add_system_tag(SLOAN_COI)
        cookies = {
            SLOAN_COI_DISPLAY: 'False',
        }

        resp = app.get('/v2/', auth=user.auth, cookies=cookies)

        assert SLOAN_COI_DISPLAY in resp.json['meta']['active_flags']
        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=True; Domain=.osf.io; Path=/; samesite=None; Secure' in cookies

    @pytest.mark.enable_quickfiles_creation
    def test_user_override_cookie_false(self, app, user, preprint):
        user.add_system_tag(f'no_{SLOAN_COI}')
        cookies = {
            SLOAN_COI_DISPLAY: 'True',
        }

        resp = app.get('/v2/', auth=user.auth, cookies=cookies)
        assert SLOAN_COI_DISPLAY not in resp.json['meta']['active_flags']
        cookies = resp.headers.getall('Set-Cookie')

        assert f' dwf_{SLOAN_COI_DISPLAY}=False; Domain=.osf.io; Path=/; samesite=None; Secure' in cookies

    def test_browseable_api(self, app):
        headers = {'accept': 'text/html'}
        resp = app.get('/v2/', headers=headers)
        assert resp.status_code == 200
