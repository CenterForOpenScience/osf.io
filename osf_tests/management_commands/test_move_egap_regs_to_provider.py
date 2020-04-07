# encoding: utf-8
import os
import shutil
import pytest
import responses
HERE = os.path.dirname(os.path.abspath(__file__))

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    RegistrationFactory,
    RegistrationProviderFactory
)

from osf.models import (
    RegistrationSchema,
    ApiOAuth2PersonalToken
)

from osf.management.commands.move_egap_regs_to_provider import (
    main as move_egap_regs
)
EGAP_PROVIDER_NAME = 'EGAP Provider'


@pytest.mark.django_db
class TestEGAPMoveToProvider:

    @pytest.fixture()
    def egap_provider(self):
        return RegistrationProviderFactory(name=EGAP_PROVIDER_NAME)


    def test_move_to_provider(self):
        pass
