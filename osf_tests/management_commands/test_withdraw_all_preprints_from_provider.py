import pytest

from osf.management.commands.withdraw_all_preprints_from_provider import withdraw_all_preprints
from osf_tests.factories import PreprintProviderFactory, PreprintFactory, AuthUserFactory

@pytest.mark.django_db
class TestWithdrawAllPreprint:

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def provider_preprint(self, preprint_provider):
        return PreprintFactory(provider=preprint_provider)

    @pytest.fixture()
    def nonprovider_preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def withdrawing_user(self):
        return AuthUserFactory()

    def test_withdraw_all_preprints(self, preprint_provider, provider_preprint, withdrawing_user):
        withdraw_all_preprints(preprint_provider._id, 10, withdrawing_user._id, 'test_comment')
        provider_preprint.reload()

        assert provider_preprint.is_retracted
        assert provider_preprint.withdrawal_justification == 'test_comment'

    def test_withdraw_no_preprints(self, preprint_provider, nonprovider_preprint, withdrawing_user):
        withdraw_all_preprints(preprint_provider._id, 10, withdrawing_user._id, 'test_comment')
        nonprovider_preprint.reload()

        assert not nonprovider_preprint.is_retracted
