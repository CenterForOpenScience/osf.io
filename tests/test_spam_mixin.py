import pytest
from unittest import mock


from osf_tests.factories import UserFactory, CommentFactory, ProjectFactory, PreprintFactory, RegistrationFactory, AuthUserFactory
from osf.models import NotableDomain, SpamStatus
from website import settings


@pytest.mark.django_db
class TestSpamState:
    @pytest.fixture(params=[
        CommentFactory,
        ProjectFactory,
        PreprintFactory,
        RegistrationFactory,
        UserFactory,
    ])
    def spammable_thing(self, request):
        spammable_factory = request.param
        return spammable_factory()

    def test_flag_spam(self, spammable_thing):
        assert not spammable_thing.is_spammy
        assert not spammable_thing.is_spam
        spammable_thing.flag_spam()
        spammable_thing.save()
        assert spammable_thing.is_spammy
        assert not spammable_thing.is_spam

    def test_confirm_ham(self, spammable_thing):
        spammable_thing.confirm_ham(save=True)
        assert spammable_thing.is_ham

    def test_confirm_spam(self, spammable_thing):
        spammable_thing.confirm_spam(save=True)
        assert spammable_thing.is_spam

    @pytest.mark.parametrize('assume_ham', (True, False))
    @pytest.mark.parametrize('spam_status, expected_props', (
            (SpamStatus.UNKNOWN, {
                'is_spam': False,
                'is_spammy': False,
                'is_ham': False,
                'is_hammy': None,  # set in the test body based on assume_ham
            }),
            (SpamStatus.FLAGGED, {
                'is_spam': False,
                'is_spammy': True,
                'is_ham': False,
                'is_hammy': False,
            }),
            (SpamStatus.SPAM, {
                'is_spam': True,
                'is_spammy': True,
                'is_ham': False,
                'is_hammy': False,
            }),
            (SpamStatus.HAM, {
                'is_spam': False,
                'is_spammy': False,
                'is_ham': True,
                'is_hammy': True,
            }),
    ))
    def test_spam_status_properties(self, spammable_thing, assume_ham, spam_status, expected_props):
        if spam_status == SpamStatus.UNKNOWN:
            expected_props['is_hammy'] = assume_ham

        with mock.patch.object(type(spammable_thing), 'is_assumed_ham', new_callable=mock.PropertyMock) as mock_assumed_ham:
            mock_assumed_ham.return_value = assume_ham
            spammable_thing.spam_status = spam_status

            assert spammable_thing.is_spam == expected_props['is_spam']
            assert spammable_thing.is_spammy == expected_props['is_spammy']
            assert spammable_thing.is_ham == expected_props['is_ham']
            assert spammable_thing.is_hammy == expected_props['is_hammy']


@pytest.mark.django_db
class TestSpamCheckEmailDomain:
    @mock.patch('osf.models.spam.SpamMixin.do_check_spam', return_value=False)
    @mock.patch.object(settings, 'SPAM_SERVICES_ENABLED', True)
    @mock.patch.object(settings, 'SPAM_CHECK_PUBLIC_ONLY', False)
    def test_trusted_domain(self, mock_do_check_spam):
        user = UserFactory()
        project = ProjectFactory()

        # spam check should normally call do_check_spam
        assert not mock_do_check_spam.called
        is_spam = project.check_spam(user, saved_fields={'title'}, request_headers={})
        assert not is_spam
        assert mock_do_check_spam.called

        # but what if we trust the user's email domain?
        user_email_address = user.emails.values_list('address', flat=True).first()
        user_email_domain = user_email_address.rpartition('@')[2].lower()
        NotableDomain.objects.create(
            domain=user_email_domain,
            note=NotableDomain.Note.ASSUME_HAM_UNTIL_REPORTED,
        )

        # should not call do_check_spam this time
        mock_do_check_spam.reset_mock()
        assert not mock_do_check_spam.called
        is_spam = project.check_spam(user, saved_fields={'title'}, request_headers={})
        assert not is_spam
        assert not mock_do_check_spam.called
