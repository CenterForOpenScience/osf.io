# -*- coding: utf-8 -*-
"""Views tests for the wiki addon."""
import pytest

from addons.wiki.exceptions import (NameInvalidError, NameMaximumLengthError,
     PageCannotRenameError, PageConflictError, PageNotFoundError)
from addons.wiki.tests.factories import NodeWikiFactory
from framework.auth import Auth
from osf.exceptions import ValidationError
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


class TestRenameNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestRenameNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_rename_name_not_found(self):
        for invalid_name in [None, '', '   ', 'Unknown Name']:
            with pytest.raises(PageNotFoundError):
                self.project.rename_node_wiki(invalid_name, None, auth=self.auth)

    def test_rename_new_name_invalid_none_or_blank(self):
        name = 'New Page'
        self.project.update_node_wiki(name, 'new content', self.auth)
        for invalid_name in [None, '', '   ']:
            with pytest.raises(ValidationError):
                self.project.rename_node_wiki(name, invalid_name, auth=self.auth)

    def test_rename_new_name_invalid_special_characters(self):
        old_name = 'old name'
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        self.project.update_node_wiki(old_name, 'some content', self.auth)
        with pytest.raises(NameInvalidError):
            self.project.rename_node_wiki(old_name, invalid_name, self.auth)

    def test_rename_name_maximum_length(self):
        old_name = 'short name'
        new_name = 'a' * 101
        self.project.update_node_wiki(old_name, 'some content', self.auth)
        with pytest.raises(NameMaximumLengthError):
            self.project.rename_node_wiki(old_name, new_name, self.auth)

    def test_rename_cannot_rename(self):
        for args in [('home', 'New Home'), ('HOME', 'New Home')]:
            with pytest.raises(PageCannotRenameError):
                self.project.rename_node_wiki(*args, auth=self.auth)

    def test_rename_page_not_found(self):
        for args in [('abc123', 'New Home'), (u'ˆ•¶£˙˙®¬™∆˙', 'New Home')]:
            with pytest.raises(PageNotFoundError):
                self.project.rename_node_wiki(*args, auth=self.auth)

    def test_rename_page(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.project.update_node_wiki(old_name, 'new content', self.auth)
        self.project.rename_node_wiki(old_name, new_name, self.auth)
        page = self.project.get_wiki_page(new_name)
        assert old_name != page.page_name
        assert new_name == page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_case_sensitive(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.project.update_node_wiki(old_name, 'new content', self.auth)
        self.project.rename_node_wiki(old_name, new_name, self.auth)
        new_page = self.project.get_wiki_page(new_name)
        assert new_name == new_page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_existing_deleted_page(self):
        old_name = 'old page'
        new_name = 'new page'
        old_content = 'old content'
        new_content = 'new content'
        # create the old page and delete it
        self.project.update_node_wiki(old_name, old_content, self.auth)
        assert old_name in self.project.wiki_pages_current
        self.project.delete_node_wiki(old_name, self.auth)
        assert old_name not in self.project.wiki_pages_current
        # create the new page and rename it
        self.project.update_node_wiki(new_name, new_content, self.auth)
        self.project.rename_node_wiki(new_name, old_name, self.auth)
        new_page = self.project.get_wiki_page(old_name)
        old_page = self.project.get_wiki_page(old_name, version=1)
        # renaming over an existing deleted page replaces it.
        assert new_content == old_page.content
        assert new_content == new_page.content
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_conflict(self):
        existing_name = 'existing page'
        new_name = 'new page'
        self.project.update_node_wiki(existing_name, 'old content', self.auth)
        assert existing_name in self.project.wiki_pages_current
        self.project.update_node_wiki(new_name, 'new content', self.auth)
        assert new_name in self.project.wiki_pages_current
        with pytest.raises(PageConflictError):
            self.project.rename_node_wiki(new_name, existing_name, self.auth)

    def test_rename_log(self):
        # Rename wiki
        self.project.update_node_wiki('wiki', 'content', self.auth)
        self.project.rename_node_wiki('wiki', 'renamed wiki', self.auth)
        # Rename is logged
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_log_specifics(self):
        self.project.update_node_wiki('wiki', 'content', self.auth)
        self.project.rename_node_wiki('wiki', 'renamed wiki', self.auth)
        page = self.project.get_wiki_page('renamed wiki')
        log = self.project.logs.latest()
        assert 'wiki_renamed' == log.action
        assert page._primary_key == log.params['page_id']


class TestDeleteNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestDeleteNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        self.versions = self.project.wiki_pages_versions

    def test_delete_log(self):
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Deletion is logged
        assert self.project.logs.latest().action == 'wiki_deleted'

    def test_delete_log_specifics(self):
        page = self.project.get_wiki_page('home')
        self.project.delete_node_wiki('home', self.auth)
        log = self.project.logs.latest()
        assert 'wiki_deleted' == log.action
        assert page._primary_key == log.params['page_id']

    def test_wiki_versions(self):
        # Number of versions is correct
        assert len(self.versions['home']) == 1
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Number of versions is still correct
        assert len(self.versions['home']) == 1

    def test_wiki_delete(self):
        page = self.project.get_wiki_page('home')
        self.project.delete_node_wiki('home', self.auth)

        # page was deleted
        assert self.project.get_wiki_page('home') is None

        log = self.project.logs.latest()

        # deletion was logged
        assert log.action == 'wiki_deleted'
        # log date is not set to the page's creation date
        assert log.date > page.date

    def test_deleted_versions(self):
        # Update wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        assert self.project.get_wiki_page('home', 2).content == 'Hola mundo'
        # Delete wiki
        self.project.delete_node_wiki('home', self.auth)
        # Check versions
        assert self.project.get_wiki_page('home',2).content == 'Hola mundo'
        assert self.project.get_wiki_page('home', 1).content == 'Hello world'
