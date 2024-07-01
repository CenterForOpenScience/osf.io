import pytest

from api.base.settings.defaults import API_BASE
from api_tests.providers.mixins import ProviderSubmissionListViewTestBaseMixin

from osf_tests.factories import (
    ProjectFactory,
    CollectionProviderFactory,
)

class TestSubmissionList(ProviderSubmissionListViewTestBaseMixin):
    provider_class = CollectionProviderFactory
    submission_class = ProjectFactory

    @pytest.fixture()
    def url(self, submission_provider):
        return f'/{API_BASE}providers/collections/{submission_provider._id}/submissions/'
