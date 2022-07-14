# -*- coding: utf-8 -*-
from django.utils import timezone
from nose.tools import *  # noqa: F403

from api.citations.utils import render_citation
from osf_tests.factories import UserFactory, PreprintFactory
from tests.base import OsfTestCase


class TestCiteprocpyMLA(OsfTestCase):
    MLA_DATE_FORMAT = '%-d {month} %Y'

    # MLA month abbreviations here
    #  http://www.pomfret.ctschool.net/computer_classes/documents/mla-abbreviationsofmonths.pdf
    MLA_MONTH_MAP = {
        1: 'Jan.',
        2: 'Feb.',
        3: 'Mar.',
        4: 'Apr.',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'Aug.',
        9: 'Sept.',
        10: 'Oct.',
        11: 'Nov.',
        12: 'Dec.',
    }

    def setUp(self):
        super(TestCiteprocpyMLA, self).setUp()
        self.user = UserFactory(fullname='John Tordoff')
        self.second_contrib = UserFactory(fullname='Carson Wentz')
        self.third_contrib = UserFactory(fullname='Nick Foles')
        self.preprint = PreprintFactory(creator=self.user, title='My Preprint')
        date = timezone.now().date()
        self.formated_date = date.strftime(self.MLA_DATE_FORMAT).format(month=self.MLA_MONTH_MAP[date.month])


    def test_render_citations_mla_one_author(self):
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John. “{}.” {}, {}. Web.'.format(
            self.preprint.title,
            self.preprint.provider.name,
            self.formated_date)
        )

        # test_suffix
        self.user.suffix = 'Junior'
        self.user.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John, Junior. “{}.” {}, {}. Web.'.format(
            self.preprint.title,
            self.preprint.provider.name,
            self.formated_date)
        )

        # test_no_middle_names
        self.user.suffix = ''
        self.user.middle_names = ''
        self.user.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John. “{}.” {}, {}. Web.'.format(
            self.preprint.title,
            self.preprint.provider.name,
            self.formated_date)
        )

    def test_citation_no_repeated_periods(self):
        self.preprint.title = 'A Study of Coffee.'
        self.preprint.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John. “{}” {}, {}. Web.'.format(
                self.preprint.title,
                self.preprint.provider.name,
                self.formated_date)
        )

    def test_citation_osf_provider(self):
        self.preprint.title = 'A Study of Coffee.'
        self.preprint.save()
        self.preprint.provider.name = 'Open Science Framework'
        self.preprint.provider.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John. “{}” {}, {}. Web.'.format(
                self.preprint.title,
                'OSF Preprints',
                self.formated_date)
        )

    def test_two_authors(self):
        self.preprint.add_contributor(self.second_contrib)
        self.preprint.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John, and Carson Wentz. “{}.” {}, {}. Web.'.format(
                self.preprint.title,
                self.preprint.provider.name,
                self.formated_date)
        )

    def test_three_authors(self):
        self.preprint.add_contributor(self.second_contrib)
        self.preprint.add_contributor(self.third_contrib)
        self.preprint.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John, et al. “{}.” {}, {}. Web.'.format(
                self.preprint.title,
                self.preprint.provider.name,
                self.formated_date)
        )

        # first name suffix
        self.user.suffix = 'Jr.'
        self.user.save()
        citation = render_citation(self.preprint, 'modern-language-association')
        assert_equal(citation, u'Tordoff, John, Jr., et al. “{}.” {}, {}. Web.'.format(
                self.preprint.title,
                self.preprint.provider.name,
                self.formated_date)
        )
