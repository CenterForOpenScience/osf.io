# -*- coding: utf-8 -*-
from api.base.settings.defaults import API_BASE
from django.utils import timezone
from api.citations.utils import display_absolute_url
from nose.tools import *  # flake8: noqa
from osf_tests.factories import AuthUserFactory, PreprintFactory
from tests.base import ApiTestCase
from framework.auth import Auth
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

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

        self.MLA_DATE_FORMAT = '%-d %b. %Y'

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B. “{}.” {}, {}. Web.'.format(
            self.node.title,
            self.published_preprint.provider.name,
            date)
        )

        # test_suffix
        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B., Junior. “{}.” {}, {}. Web.'.format(
            self.node.title,
            self.published_preprint.provider.name,
            date)
        )

        # test_no_middle_names
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes. “{}.” {}, {}. Web.'.format(
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
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B. “{}” {}, {}. Web.'.format(
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
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B. “{}” {}, {}. Web.'.format(
                self.node.title,
                'OSF Preprints',
                date)
        )

    def test_two_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B., and Darla T. T. Jenkins, Junior. “{}.” {}, {}. Web.'.format(
                self.node.title,
                self.published_preprint.provider.name,
                date)
        )

    def test_three_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        print date
        assert_equal(citation, u'McGee, Grapes C. B., et al. “{}.” {}, {}. Web.'.format(
                self.node.title,
                self.published_preprint.provider.name,
                date)
        )

        # first name suffix
        self.admin_contributor.suffix = 'Jr.'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime(self.MLA_DATE_FORMAT)
        assert_equal(citation, u'McGee, Grapes C. B., Jr., et al. “{}.” {}, {}. Web.'.format(
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
        self.node.title = 'A Study of Coffee'
        self.node.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
                     API_BASE, self.published_preprint._id)

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B. ({}). {}. {}'.format(
                date,
                self.node.title,
                'https://doi.org/' + self.published_preprint.article_doi
                )
        )

        # test_suffix
        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B., Junior. ({}). {}. {}'.format(
            date,
            self.node.title,
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )

        # test_no_middle_names
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. ({}). {}. {}'.format(
            date,
            self.node.title,
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )

    def test_two_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B., & Jenkins, D. T. T., Junior. ({}). {}. {}'.format(
            date,
            self.node.title,
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )

    def test_three_authors_and_title_with_period(self):
        self.node.title = 'This Title Ends in a Period.'
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B., Jenkins, D. T. T., Junior, & Schematics, L. R. ({}). {}. {}'.format(
            date,
            'This Title Ends in a Period',
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )

    def test_seven_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        for i in range(1,5):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = 'Taylor{}'.format(i)
            new_user.save()
            self.node.add_contributor(new_user)
        self.node.save()

        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B., Jenkins, D. T. T., Junior, Schematics, L. R., Taylor1, J., Taylor2, J., Taylor3, J., & Taylor4, J. ({}). {}. {}'.format(
            date,
            self.node.title,
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )

    def test_eight_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        for i in range(1,6):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = 'Taylor{}'.format(i)
            new_user.save()
            self.node.add_contributor(new_user)
        self.node.save()

        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date().strftime('%Y, %B %-d')
        assert_equal(citation, u'McGee, G. C. B., Jenkins, D. T. T., Junior, Schematics, L. R., Taylor1, J., Taylor2, J., Taylor3, J., … Taylor5, J. ({}). {}. {}'.format(
            date,
            self.node.title,
            'https://doi.org/' + self.published_preprint.article_doi
            )
        )


class TestPreprintCitationContentChicago(ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContentChicago, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.node = self.published_preprint.node
        self.node.title = 'A Study of Coffee'
        self.node.save()

        self.admin_contributor.given_name = 'Grapes'
        self.admin_contributor.middle_names = ' Coffee Beans '
        self.admin_contributor.family_name = 'McGee'
        self.admin_contributor.save()
        self.published_preprint_url = '/{}preprints/{}/citation/chicago-author-date/'.format(
                     API_BASE, self.published_preprint._id)

        self.second_contrib = AuthUserFactory()
        self.second_contrib.given_name = 'Darla'
        self.second_contrib.middle_names = 'Texas Toast'
        self.second_contrib.family_name = 'Jenkins'
        self.second_contrib.suffix = 'Junior'
        self.second_contrib.save()

        self.third_contrib = AuthUserFactory()
        self.third_contrib.given_name = 'Lilith'
        self.third_contrib.middle_names = 'Radar'
        self.third_contrib.family_name = 'Schematics'
        self.third_contrib.save()

    def test_one_author(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C. B. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )

        # test_suffix
        self.admin_contributor.suffix = 'Junior'
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C. B., Junior. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )

        # test_no_middle_names
        self.admin_contributor.suffix = ''
        self.admin_contributor.middle_names = ''
        self.admin_contributor.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )

    def test_two_authors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C. B., and Darla T. T. Jenkins, Junior. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )

    def test_three_authors_and_title_with_period(self):
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        self.node.title = 'This Preprint ends in a Period.'
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C. B., Darla T. T. Jenkins, Junior, and Lilith R. Schematics. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                'This Preprint Ends in a Period',
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )

    def test_eleven_contributors(self):
        self.node.add_contributor(self.second_contrib)
        self.node.add_contributor(self.third_contrib)
        for i in range(1,9):
            new_user = AuthUserFactory()
            new_user.given_name = 'James'
            new_user.family_name = 'Taylor{}'.format(i)
            new_user.save()
            self.node.add_contributor(new_user)
        self.node.save()
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        citation = res.json['data']['attributes']['citation']
        date = timezone.now().date()
        assert_equal(citation, u'McGee, Grapes C. B., Darla T. T. Jenkins, Junior, Lilith R. Schematics, James Taylor1, James Taylor2, James Taylor3, James Taylor4, et al. {}. “{}.” {}. {}. {}.'.format(
                date.strftime('%Y'),
                self.node.title,
                self.published_preprint.provider.name,
                date.strftime('%B %-d'),
                'doi:' + self.published_preprint.article_doi
                )
        )
