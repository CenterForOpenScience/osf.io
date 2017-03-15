from nose.tools import *  # flake8: noqa

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from api_tests.preprints.filters.test_filters import PreprintsListFilteringMixin
from website.preprints.model import PreprintService

from tests.base import ApiTestCase
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)


class TestPreprintsListFiltering(PreprintsListFilteringMixin, ApiTestCase):

    def _setUp(self):
        self.user = AuthUserFactory()
        self.provider = PreprintProviderFactory(name='Sockarxiv')

        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()

        self.preprint = PreprintFactory(creator=self.user, provider=self.provider, subjects=[[self.subject._id]])
        self.preprint_two = PreprintFactory(creator=self.user, filename='tough.txt', provider=self.provider, subjects=[[self.subject_two._id]])

        self.preprint_two.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.save()

        self.preprint_three = PreprintFactory(creator=self.user, filename='darn.txt', provider=self.provider, subjects=[[self.subject._id], [self.subject_two._id]])
        self.preprint_three.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.is_published = False
        self.preprint_three.save()

        self.url = '/{}preprint_providers/{}/preprints/?version=2.2&'.format(API_BASE, self.provider._id)

    def test_provider_filter_equals_returns_one(self):
      pass

    def test_provider_filter_equals_returns_multiple(self):
        expected = set([self.preprint._id, self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.provider_url, self.provider._id), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)
