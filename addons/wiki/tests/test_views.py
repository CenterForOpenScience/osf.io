"""Views tests for the wiki addon."""
import pytest

from addons.wiki.exceptions import (NameEmptyError, NameInvalidError,
                                            NameMaximumLengthError,
                                            PageCannotRenameError,
                                            PageConflictError,
                                            PageNotFoundError)
from addons.wiki.tests.factories import NodeWikiFactory
from framework.auth import Auth
from osf.models import Guid
from osf_tests.factories import AuthUserFactory, UserFactory, ProjectFactory, NodeFactory, CommentFactory
from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db


class TestUpdateNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestUpdateNodeWiki, self).setUp()
        # Create project with component
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert project1.get_wiki_page('home') is None

    def test_default_is_current(self):
        assert self.project.get_wiki_page('home').is_current is True
        self.project.update_node_wiki('home', 'Hello world 2', self.auth)
        assert self.project.get_wiki_page('home').is_current is True
        self.project.update_node_wiki('home', 'Hello world 3', self.auth)

    def test_wiki_content(self):
        # Wiki has correct content
        assert self.project.get_wiki_page('home').content == 'Hello world'
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # Both versions have the expected content
        assert self.project.get_wiki_page('home', 2).content == 'Hola mundo'
        assert self.project.get_wiki_page('home', 1).content == 'Hello world'

    def test_current(self):
        # Wiki is current
        assert self.project.get_wiki_page('home', 1).is_current is True
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # New version is current, old version is not
        assert self.project.get_wiki_page('home', 2).is_current is True
        assert self.project.get_wiki_page('home', 1).is_current is False

    def test_update_log(self):
        # Updates are logged
        assert self.project.logs.latest().action == 'wiki_updated'
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # There are two update logs
        assert self.project.logs.filter(action='wiki_updated').count() == 2

    def test_update_log_specifics(self):
        page = self.project.get_wiki_page('home')
        log = self.project.logs.latest()
        assert 'wiki_updated' == log.action
        assert page._primary_key == log.params['page_id']

    def test_wiki_versions(self):
        # Number of versions is correct
        assert len(self.versions['home']) == 1
        # Update wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        # Number of versions is correct
        assert len(self.versions['home']) == 2
        # Versions are different
        assert self.versions['home'][0] != self.versions['home'][1]

    def test_update_two_node_wikis(self):
        # user updates a second wiki for the same node
        self.project.update_node_wiki('second', 'Hola mundo', self.auth)
        # each wiki only has one version
        assert len(self.versions['home']) == 1
        assert len(self.versions['second']) == 1
        # There are 2 logs saved
        assert self.project.logs.filter(action='wiki_updated').count() == 2
        # Each wiki has the expected content
        assert self.project.get_wiki_page('home').content == 'Hello world'
        assert self.project.get_wiki_page('second').content == 'Hola mundo'

    def test_update_name_invalid(self):
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        with pytest.raises(NameInvalidError):
            self.project.update_node_wiki(invalid_name, 'more valid content', self.auth)

    def test_update_wiki_updates_comments_and_user_comments_viewed_timestamp(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki = NodeWikiFactory(node=project, page_name='test')
        comment = CommentFactory(node=project, target=Guid.load(wiki._id), user=UserFactory())

        # user views comments -- sets user.comments_viewed_timestamp
        url = project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki._id
        }, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        assert wiki._id in self.user.comments_viewed_timestamp

        # user updates the wiki
        project.update_node_wiki('test', 'Updating wiki', self.auth)
        comment.reload()
        self.user.reload()

        new_version_id = project.wiki_pages_current['test']
        assert new_version_id in self.user.comments_viewed_timestamp
        assert wiki._id not in self.user.comments_viewed_timestamp
        assert comment.target.referent._id == new_version_id

    # Regression test for https://openscience.atlassian.net/browse/OSF-6138
    def test_update_wiki_updates_contributor_comments_viewed_timestamp(self):
        contributor = AuthUserFactory()
        project = ProjectFactory(creator=self.user, is_public=True)
        project.add_contributor(contributor)
        project.save()
        wiki = NodeWikiFactory(node=project, page_name='test')
        comment = CommentFactory(node=project, target=Guid.load(wiki._id), user=self.user)

        # user views comments -- sets user.comments_viewed_timestamp
        url = project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki._id
        }, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        assert wiki._id in self.user.comments_viewed_timestamp

        # contributor views comments -- sets contributor.comments_viewed_timestamp
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki._id
        }, auth=contributor.auth)
        contributor.reload()
        assert wiki._id in contributor.comments_viewed_timestamp

        # user updates the wiki
        project.update_node_wiki('test', 'Updating wiki', self.auth)
        comment.reload()
        contributor.reload()

        new_version_id = project.wiki_pages_current['test']
        assert new_version_id in contributor.comments_viewed_timestamp
        assert wiki._id not in contributor.comments_viewed_timestamp
        assert comment.target.referent._id == new_version_id
