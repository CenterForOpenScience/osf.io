import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderSubmissionListViewTestBaseMixin

from osf_tests.factories import (
    RegistrationFactory,
    RegistrationProviderFactory,
)


class TestSubmissionList(ProviderSubmissionListViewTestBaseMixin):
    provider_class = RegistrationProviderFactory
    submission_class = RegistrationFactory

    @pytest.fixture()
    def url(self, submission_provider):
        return '/{}providers/registrations/{}/submissions/'.format(API_BASE, submission_provider._id)
