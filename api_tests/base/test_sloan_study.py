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
        app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_DATA in tags
        assert SLOAN_PREREG in tags
        assert SLOAN_COI in tags

        resp = app.get('/v2/', auth=user.auth, headers=headers)

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
        app.get('/v2/', auth=user.auth, headers=headers)

        tags = user.all_tags.all().values_list('name', flat=True)

        assert SLOAN_DATA not in tags
        assert SLOAN_PREREG not in tags
        assert SLOAN_COI not in tags

        resp = app.get('/v2/', auth=user.auth, headers=headers)

        assert SLOAN_DATA not in resp.json['meta']['active_flags']
        assert SLOAN_PREREG not in resp.json['meta']['active_flags']
        assert SLOAN_COI not in resp.json['meta']['active_flags']

        cookies = resp.headers.getall('Set-Cookie')

        assert f' {SLOAN_DATA}=True; Path=/' not in cookies
        assert f' {SLOAN_PREREG}=True; Path=/' not in cookies
        assert f' {SLOAN_COI}=True; Path=/' not in cookies
