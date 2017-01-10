import pytest

from modularodm.exceptions import ValidationValueError
from osf_tests.factories import NodeFactory
from addons.wiki.models import NodeWikiPage

pytestmark = pytest.mark.django_db

# from website/addons/wiki/tests/test_wiki.py
class TestNodeWikiPageModel:

    def test_page_name_cannot_be_greater_than_100_characters(self):
        bad_name = 'a' * 101
        page = NodeWikiPage(page_name=bad_name)
        with pytest.raises(ValidationValueError):
            page.save()

    def test_is_current_with_single_version(self):
        node = NodeFactory()
        page = NodeWikiPage(page_name='foo', node=node)
        page.save()
        node.wiki_pages_current['foo'] = page._id
        node.wiki_pages_versions['foo'] = [page._id]
        node.save()
        assert page.is_current is True

    def test_is_current_with_multiple_versions(self):
        node = NodeFactory()
        ver1 = NodeWikiPage(page_name='foo', node=node)
        ver2 = NodeWikiPage(page_name='foo', node=node)
        ver1.save()
        ver2.save()
        node.wiki_pages_current['foo'] = ver2._id
        node.wiki_pages_versions['foo'] = [ver1._id, ver2._id]
        node.save()
        assert ver1.is_current is False
        assert ver2.is_current is True

    def test_is_current_deleted_page(self):
        node = NodeFactory()
        ver = NodeWikiPage(page_name='foo', node=node)
        ver.save()
        # Simulate a deleted page by not adding ver to
        # node.wiki_pages_current and node.wiki_pages_versions
        assert ver.is_current is False
