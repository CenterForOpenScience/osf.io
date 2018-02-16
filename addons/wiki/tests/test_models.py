import pytest
import pytz
import datetime
from addons.wiki.exceptions import NameMaximumLengthError

from addons.wiki.models import WikiPage
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from osf_tests.factories import NodeFactory, UserFactory, ProjectFactory
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

# from website/addons/wiki/tests/test_wiki.py
class TestWikiPageModel:

    def test_page_name_cannot_be_greater_than_100_characters(self):
        bad_name = 'a' * 101
        page = WikiPage(page_name=bad_name)
        with pytest.raises(NameMaximumLengthError):
            page.save()

    def test_is_current_with_single_version(self):
        user = UserFactory()
        node = NodeFactory()
        page = WikiPage(page_name='foo', node=node)
        page.save()
        version = page.create_version(user=user, content='hello')
        assert version.is_current is True

    def test_is_current_with_multiple_versions(self):
        user = UserFactory()
        node = NodeFactory()
        page = WikiPage(page_name='foo', node=node)
        page.save()
        ver1 = page.create_version(user=user, content='draft1')
        ver2 = page.create_version(user=user, content='draft2')
        assert ver1.is_current is False
        assert ver2.is_current is True

    def test_is_current_deleted_page(self):
        user = UserFactory()
        node = NodeFactory()
        page = WikiPage(page_name='foo', node=node)
        page.save()
        ver1 = page.create_version(user=user, content='draft1')
        page.deleted = datetime.datetime(2017, 1, 1, 1, 00, tzinfo=pytz.utc)
        page.save()
        assert ver1.is_current is False


class TestWikiPage(OsfTestCase):

    def setUp(self):
        super(TestWikiPage, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.wiki = WikiFactory(user=self.user, node=self.project)

    def test_wiki_factory(self):
        wiki = WikiFactory()
        assert wiki.page_name == 'home'
        assert bool(wiki.user)
        assert bool(wiki.node)

    def test_wiki_version_factory(self):
        version = WikiVersionFactory()
        assert version.identifier == 1
        assert version.content == 'First draft of wiki'
        assert bool(version.user)
        assert bool(version.wiki_page)

    def test_url(self):
        assert self.wiki.url == '{project_url}wiki/home/'.format(project_url=self.project.url)

    def test_url_for_wiki_page_name_with_spaces(self):
        wiki = WikiFactory(user=self.user, node=self.project, page_name='Test Wiki')
        url = '{}wiki/{}/'.format(self.project.url, wiki.page_name)
        assert wiki.url == url

    def test_url_for_wiki_page_name_with_special_characters(self):
        wiki = WikiFactory(user=self.user, node=self.project)
        wiki.page_name = 'Wiki!@#$%^&*()+'
        wiki.save()
        url = '{}wiki/{}/'.format(self.project.url, wiki.page_name)
        assert wiki.url == url
