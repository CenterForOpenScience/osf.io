# encoding: utf-8
import pytest

from osf_tests.factories import (
    RegistrationFactory,
    RegistrationProviderFactory
)

from osf.models import (
    RegistrationSchema,
    RegistrationProvider
)

from osf.management.commands.move_egap_regs_to_provider import (
    main as move_egap_regs
)


@pytest.mark.django_db
class TestEGAPMoveToProvider:

    @pytest.fixture()
    def egap_provider(self):
        return RegistrationProviderFactory(_id='egap')

    @pytest.fixture()
    def non_egap_provider(self):
        return RegistrationProvider.get_default()

    @pytest.fixture()
    def egap_reg(self):
        egap_schema = RegistrationSchema.objects.filter(
            name='EGAP Registration'
        ).order_by(
            '-schema_version'
        )[0]
        cos = RegistrationProvider.get_default()
        return RegistrationFactory(schema=egap_schema, provider=cos)

    @pytest.fixture()
    def egap_non_reg(self, non_egap_provider):
        return RegistrationFactory(provider=non_egap_provider)

    def test_move_to_provider(self, egap_provider, egap_reg, non_egap_provider, egap_non_reg):
        assert egap_reg.provider != egap_provider
        assert egap_non_reg.provider != egap_provider

        move_egap_regs(dry_run=False)

        egap_reg.refresh_from_db()
        assert egap_reg.provider == egap_provider
        assert egap_non_reg.provider != egap_provider
