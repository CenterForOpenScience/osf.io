# -*- coding: utf-8 -*-
from api.base.settings.defaults import API_BASE
from django.utils import timezone
from api.citations.utils import display_absolute_url
from nose.tools import *  # flake8: noqa
from osf_tests.factories import AuthUserFactory, PreprintFactory
from tests.base import ApiTestCase
from datetime import datetime


class PreprintCitationsMixin(object):

    def setUp(self):
        super(PreprintCitationsMixin, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.unpublished_preprint = PreprintFactory(
            creator=self.admin_contributor, is_published=False)

    def test_unauthenticated_can_view_published_preprint_citations(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)

    def test_unauthenticated_cannot_view_unpublished_preprint_citations(self):
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_preprint_citations_are_read_only(self):
        post_res = self.app.post_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(post_res.status_code, 405)
        put_res = self.app.put_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(put_res.status_code, 405)
        delete_res = self.app.delete_json_api(
            self.published_preprint_url,
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(delete_res.status_code, 405)


class TestPreprintCitations(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitations, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.unpublished_preprint._id)

    def test_citation_publisher_is_preprint_provider(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['attributes']['publisher'],
            self.published_preprint.provider.name)

    def test_citation_url_is_preprint_url_not_project(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['links']['self'],
            display_absolute_url(self.published_preprint))


class TestPreprintCitationContent(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContent, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.unpublished_preprint._id)

    def test_citation_contains_correct_date(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        expected_date = self.published_preprint.node.logs.latest().date.strftime('%Y, %B %-d')
        assert_true(
            expected_date in res.json['data']['attributes']['citation'])

        self.published_preprint.original_publication_date = datetime(
            2017, 12, 24)
        self.published_preprint.save()

        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        expected_date = self.published_preprint.original_publication_date.strftime(
            '%Y, %B %-d')
        assert_true(
            expected_date in res.json['data']['attributes']['citation'])


class TestPreprintCitationContentMLA(ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContentMLA, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.node = self.published_preprint.node
        self.node.title = "My Preprint"
        self.node.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = '/{}preprints/{}/citation/modern-language-association/'.format(
                     API_BASE, self.published_preprint._id)

    def test_citation_contains_correctly_formats_middle_names(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%-d %B %Y')
        assert_equal(citation, u'McGee, Grapes C B. “{}” {}, {}. Web.'.format(
                self.node.title,
                self.published_preprint.provider.name,
                date)
        )

    def test_citation_no_repeated_periods(self):
        self.node.title = 'A Study of Coffee.'
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%-d %B %Y')
        assert_equal(citation, u'McGee, Grapes C B. “{}” {}, {}. Web.'.format(
                self.node.title,
                self.published_preprint.provider.name,
                date)
        )

    def test_citation_osf_provider(self):
        self.node.title = 'A Study of Coffee.'
        self.node.save()
        self.published_preprint.provider.name = 'Open Science Framework'
        self.published_preprint.provider.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%-d %B %Y')
        assert_equal(citation, u'McGee, Grapes C B. “{}” {}, {}. Web.'.format(
                self.node.title,
                self.published_preprint.provider.name,
                date)
        )


class TestPreprintCitationContentAPA(ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContentAPA, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.node = self.published_preprint.node

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
                     API_BASE, self.published_preprint._id)

    def test_api_citation_particulars(self):
        self.node.title = 'A Study of Coffee.'
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B. ({}). {} {}'.format(
                date,
                self.node.title,
                'http://doi.org/' + self.published_preprint.article_doi
                )
        )


class TestPreprintCitationContentChicago(ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContentChicago, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.node = self.published_preprint.node

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = '/{}preprints/{}/citation/chicago-author-date/'.format(
                     API_BASE, self.published_preprint._id)

    def test_api_citation_particulars(self):
        self.node.title = 'A Study of Coffee.'
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C B. {}. “{}” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )
