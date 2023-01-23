import mock
import pytest

from django.utils import timezone
from past.builtins import basestring

from osf.models import Institution
from osf_tests.factories import InstitutionFactory, AuthUserFactory, UserFactory
from website import mails, settings


@pytest.mark.django_db
def test_factory():
    inst = InstitutionFactory()
    assert isinstance(inst.name, basestring)
    assert len(inst.domains) > 0
    assert len(inst.email_domains) > 0


@pytest.mark.django_db
def test_querying_on_domains():
    inst = InstitutionFactory(domains=['foo.test'])
    result = Institution.objects.filter(domains__contains=['foo.test'])
    assert inst in result


@pytest.mark.django_db
def test_institution_banner_path_none():
    inst = InstitutionFactory(banner_name='kittens.png')
    assert inst.banner_path is not None
    inst.banner_name = None
    assert inst.banner_path is None


@pytest.mark.django_db
def test_institution_logo_path_none():
    inst = InstitutionFactory(logo_name='kittens.png')
    assert inst.logo_path is not None
    inst.logo_name = None
    assert inst.logo_path is None


@pytest.mark.django_db
def test_institution_logo_path():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields/osf-shield.png'
    assert inst.logo_path == expected_logo_path


@pytest.mark.django_db
def test_institution_logo_path_rounded_corners():
    inst = InstitutionFactory(logo_name='osf-shield.png')
    expected_logo_path = '/static/img/institutions/shields-rounded-corners/osf-shield-rounded-corners.png'
    assert inst.logo_path_rounded_corners == expected_logo_path


@pytest.mark.django_db
def test_institution_banner_path():
    inst = InstitutionFactory(banner_name='osf-banner.png')
    expected_banner_path = '/static/img/institutions/banners/osf-banner.png'
    assert inst.banner_path == expected_banner_path


class TestInstitutionPermissions:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution_admin_user(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.mark.django_db
    def test_group_member_has_perms(self, institution, institution_admin_user):
        assert institution_admin_user.has_perm('view_institutional_metrics', institution)

    @pytest.mark.django_db
    def test_non_group_member_doesnt_have_perms(self, institution, user):
        assert user.has_perm('view_institutional_metrics', institution) is False


@pytest.mark.django_db
class TestInstitutionManager:

    def test_deactivated_institution_not_in_default_queryset(self):
        institution = InstitutionFactory()
        assert institution in Institution.objects.all()

        institution.deactivated = timezone.now()
        institution.save()
        assert institution not in Institution.objects.all()

    def test_deactivated_institution_in_all_institutions(self):
        institution = InstitutionFactory()
        assert institution in Institution.objects.get_all_institutions()

        institution.deactivated = timezone.now()
        institution.save()
        assert institution in Institution.objects.get_all_institutions()

    def test_deactivate_institution(self):
        institution = InstitutionFactory()
        with mock.patch.object(
                institution,
                '_send_deactivation_email',
                return_value=None
        ) as mock__send_deactivation_email:
            institution.deactivate()
            assert institution.deactivated is not None
            assert mock__send_deactivation_email.called

    def test_reactivate_institution(self):
        institution = InstitutionFactory()
        institution.deactivated = timezone.now()
        institution.save()
        institution.reactivate()
        assert institution.deactivated is None

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @mock.patch('website.mails.send_mail', return_value=None, side_effect=mails.send_mail)
    def test_send_deactivation_email_call_count(self, mock_send_mail):
        institution = InstitutionFactory()
        user_1 = UserFactory()
        user_1.affiliated_institutions.add(institution)
        user_1.save()
        user_2 = UserFactory()
        user_2.affiliated_institutions.add(institution)
        user_2.save()
        institution._send_deactivation_email()
        assert mock_send_mail.call_count == 2

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @mock.patch('website.mails.send_mail', return_value=None, side_effect=mails.send_mail)
    def test_send_deactivation_email_call_args(self, mock_send_mail):
        institution = InstitutionFactory()
        user = UserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        institution._send_deactivation_email()
        forgot_password = 'forgotpassword' if settings.DOMAIN.endswith('/') else '/forgotpassword'
        mock_send_mail.assert_called_with(
            to_addr=user.username,
            mail=mails.INSTITUTION_DEACTIVATION,
            user=user,
            forgot_password_link='{}{}'.format(settings.DOMAIN, forgot_password),
            osf_support_email=settings.OSF_SUPPORT_EMAIL
        )

    def test_deactivate_inactive_institution_noop(self):
        institution = InstitutionFactory()
        institution.deactivated = timezone.now()
        institution.save()
        with mock.patch.object(institution, 'save', return_value=None) as mock_save:
            institution.deactivate()
            assert not mock_save.called

    def test_reactivate_active_institution_noop(self):
        institution = InstitutionFactory()
        institution.deactivated = None
        institution.save()
        with mock.patch.object(institution, 'save', return_value=None) as mock_save:
            institution.reactivate()
            assert not mock_save.called
