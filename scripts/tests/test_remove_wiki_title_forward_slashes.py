from nose.tools import *

from framework.mongo import database as db

from scripts.remove_wiki_title_forward_slashes import main

from tests.base import OsfTestCase
from tests.factories import NodeWikiFactory, ProjectFactory


class TestRemoveWikiTitleForwardSlashes(OsfTestCase):

    def test_forward_slash_is_removed_from_wiki_title(self):
        project = ProjectFactory()
        wiki = NodeWikiFactory(node=project)

        invalid_name = 'invalid/name'
        db.nodewikipage.update({'_id': wiki._id}, {'$set': {'page_name': invalid_name}})
        project.wiki_pages_current['invalid/name'] = project.wiki_pages_current[wiki.page_name]
        project.wiki_pages_versions['invalid/name'] = project.wiki_pages_versions[wiki.page_name]
        project.save()

        main()
        wiki.reload()

        assert_equal(wiki.page_name, 'invalidname')
        assert_in('invalidname', project.wiki_pages_current)
        assert_in('invalidname', project.wiki_pages_versions)

    def test_valid_wiki_title(self):
        project = ProjectFactory()
        wiki = NodeWikiFactory(node=project)
        page_name = wiki.page_name
        main()
        wiki.reload()
        assert_equal(page_name, wiki.page_name)
        assert_in(page_name, project.wiki_pages_current)
        assert_in(page_name, project.wiki_pages_versions)
