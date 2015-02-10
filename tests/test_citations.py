import datetime
from nose.tools import *  # noqa

from scripts import parse_citation_styles
from website import citations
from website.util import api_url_for
from website.citations.utils import datetime_to_csl
from website.models import Node, User

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory
from tests.test_features import requires_csl_styles


bibtex_template = '''@misc{{{id},
  title={{{title}}},
  url={{{url}}},
  publisher={{Open Science Framework}},
  author={{{authors}}},
  year={{{year}}},
  month={{{month}}}
}}'''


class CitationsTestCase(OsfTestCase):
    def setUp(self):
        super(CitationsTestCase, self).setUp()
        self.node = ProjectFactory()

    def tearDown(self):
        super(CitationsTestCase, self).tearDown()
        Node.remove()

    @requires_csl_styles
    def test_render_bibtex(self):
        # render a node citation as BibTeX
        expected = bibtex_template.format(
            id='_'.join((self.node.creator.family_name.lower(),
                         str(self.node.logs[-1].date.year))),
            title=self.node.title,
            url=self.node.display_absolute_url,
            authors=', '.join((self.node.creator.family_name,
                               self.node.creator.given_name)),
            year=str(self.node.logs[-1].date.year),
            month=str(self.node.logs[-1].date.strftime('%b')),
        )

        assert_equal(
            citations.render(self.node, style='bibtex'),
            expected,
        )


class CitationsUtilsTestCase(OsfTestCase):
    def test_datetime_to_csl(self):
        # Convert a datetime instance to csl's date-variable schema
        now = datetime.datetime.utcnow()

        assert_equal(
            datetime_to_csl(now),
            {'date-parts': [[now.year, now.month, now.day]]},
        )


class CitationsNodeTestCase(OsfTestCase):
    def setUp(self):
        super(CitationsNodeTestCase, self).setUp()
        self.node = ProjectFactory()

    def tearDown(self):
        super(CitationsNodeTestCase, self).tearDown()
        Node.remove()
        User.remove()

    def test_csl_single_author(self):
        # Nodes with one contributor generate valid CSL-data
        assert_equal(
            self.node.csl,
            {
                'publisher': 'Open Science Framework',
                'author': [{
                    'given': self.node.creator.given_name,
                    'family': self.node.creator.family_name,
                }],
                'URL': self.node.display_absolute_url,
                'issued': datetime_to_csl(self.node.logs[-1].date),
                'title': self.node.title,
                'type': 'webpage',
                'id': self.node._id,
            },
        )

    def test_csl_multiple_authors(self):
        # Nodes with multiple contributors generate valid CSL-data
        user = UserFactory()
        self.node.add_contributor(user)
        self.node.save()

        assert_equal(
            self.node.csl,
            {
                'publisher': 'Open Science Framework',
                'author': [
                    {
                        'given': self.node.creator.given_name,
                        'family': self.node.creator.family_name,
                    },
                    {
                        'given': user.given_name,
                        'family': user.family_name,
                    }
                ],
                'URL': self.node.display_absolute_url,
                'issued': datetime_to_csl(self.node.logs[-1].date),
                'title': self.node.title,
                'type': 'webpage',
                'id': self.node._id,
            },
        )


class CitationsUserTestCase(OsfTestCase):
    def setUp(self):
        super(CitationsUserTestCase, self).setUp()
        self.user = UserFactory()

    def tearDown(self):
        super(CitationsUserTestCase, self).tearDown()
        User.remove()

    def test_user_csl(self):
        # Convert a User instance to csl's name-variable schema
        assert_equal(
            self.user.csl_name,
            {
                'given': self.user.given_name,
                'family': self.user.family_name,
            },
        )


class CitationsViewsTestCase(OsfTestCase):
    @classmethod
    def setUpClass(cls):
        super(CitationsViewsTestCase, cls).setUpClass()
        # populate the DB with parsed citation styles
        try:
            parse_citation_styles.main()
        except OSError:
            pass

    @requires_csl_styles
    def test_list_styles(self):
        # Response includes a list of available citation styles
        response = self.app.get(api_url_for('list_citation_styles'))

        assert_true(response.json)

        assert_equal(
            len(
                [
                    style for style in response.json['styles']
                    if style.get('id') == 'bibtex']
            ),
            1,
        )

    @requires_csl_styles
    def test_citation_view(self):
        # Response includes a valid text citation in the given format
        node = ProjectFactory(is_public=True)
        response = self.app.get(api_url_for('node_citation',
                                            pid=node._id,
                                            style='bibtex'))

        assert_equal(
            response.json,
            {'citation': citations.render(node, style='bibtex')}
        )
