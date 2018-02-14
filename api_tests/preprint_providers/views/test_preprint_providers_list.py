import pytest

from api.base.settings.defaults import API_BASE
from api_tests.reviews.mixins.filter_mixins import ReviewProviderFilterMixin


class TestReviewProviderFilters(ReviewProviderFilterMixin):

    @pytest.fixture()
    def url(self):
        return '/{}preprint_providers/'.format(API_BASE)
