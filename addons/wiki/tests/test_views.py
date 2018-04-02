# -*- coding: utf-8 -*-
"""Views tests for the wiki addon."""
import pytest
import mock
import pytz
import datetime
from django.utils import timezone

from addons.wiki.exceptions import (NameInvalidError, NameMaximumLengthError,
     PageCannotRenameError, PageConflictError, PageNotFoundError)
from addons.wiki.tests.factories import WikiVersionFactory, WikiFactory
from addons.wiki.utils import serialize_wiki_widget
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
        self.wiki_page = self.project.get_wiki_page('home')

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert project1.get_wiki_version('home') is None

    def test_default_is_current(self):
        assert self.project.get_wiki_version('home').is_current is True
        self.project.update_node_wiki('home', 'Hello world 2', self.auth)
        assert self.project.get_wiki_version('home').is_current is True
        self.project.update_node_wiki('home', 'Hello world 3', self.auth)
        assert self.project.get_wiki_version('home').is_current is True

    def test_wiki_content(self):
        # Wiki has correct content
        assert self.project.get_wiki_version('home').content == 'Hello world'
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # Both versions have the expected content
        assert self.project.get_wiki_version('home', 2).content == 'Hola mundo'
        assert self.project.get_wiki_version('home', 1).content == 'Hello world'

    def test_current(self):
        # Wiki is current
        assert self.project.get_wiki_version('home', 1).is_current is True
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.auth)
        # New version is current, old version is not
        assert self.project.get_wiki_version('home', 2).is_current is True
        assert self.project.get_wiki_version('home', 1).is_current is False

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
        assert self.wiki_page.current_version_number == 1
        # Update wiki
        self.project.update_node_wiki('home', 'Hello world', self.auth)
        # Number of versions is correct
        assert self.wiki_page.current_version_number == 2
        # Versions are different
        versions = self.wiki_page.get_versions()
        assert versions[0]._id != versions[1]._id

    def test_update_two_node_wikis(self):
        # user updates a second wiki for the same node
        self.project.update_node_wiki('second', 'Hola mundo', self.auth)
        # each wiki only has one version
        assert self.wiki_page.current_version_number == 1
        assert self.project.get_wiki_page('second').current_version_number == 1
        # There are 2 logs saved
        assert self.project.logs.filter(action='wiki_updated').count() == 2
        # Each wiki has the expected content
        assert self.project.get_wiki_version('home').content == 'Hello world'
        assert self.project.get_wiki_version('second').content == 'Hola mundo'

    def test_update_name_invalid(self):
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        with pytest.raises(NameInvalidError):
            self.project.update_node_wiki(invalid_name, 'more valid content', self.auth)

    def test_update_wiki_updates_comments_and_user_comments_viewed_timestamp(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki_page = WikiFactory(node=project, page_name='test')
        wiki = WikiVersionFactory(wiki_page=wiki_page)
        comment = CommentFactory(node=project, target=Guid.load(wiki_page._id), user=UserFactory())

        # user views comments -- sets user.comments_viewed_timestamp
        url = project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki_page._id
        }, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        assert wiki_page._id in self.user.comments_viewed_timestamp

        # user updates the wiki
        project.update_node_wiki('test', 'Updating wiki', self.auth)
        comment.reload()
        self.user.reload()
        assert wiki_page._id in self.user.comments_viewed_timestamp
        assert comment.target.referent._id == wiki_page._id

    # Regression test for https://openscience.atlassian.net/browse/OSF-6138
    def test_update_wiki_updates_contributor_comments_viewed_timestamp(self):
        contributor = AuthUserFactory()
        project = ProjectFactory(creator=self.user, is_public=True)
        project.add_contributor(contributor)
        project.save()
        wiki_page = WikiFactory(node=project, page_name='test')
        wiki = WikiVersionFactory(wiki_page=wiki_page)
        comment = CommentFactory(node=project, target=Guid.load(wiki_page._id), user=self.user)

        # user views comments -- sets user.comments_viewed_timestamp
        url = project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki_page._id
        }, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        assert wiki_page._id in self.user.comments_viewed_timestamp

        # contributor views comments -- sets contributor.comments_viewed_timestamp
        res = self.app.put_json(url, {
            'page': 'wiki',
            'rootId': wiki_page._id
        }, auth=contributor.auth)
        contributor.reload()
        assert wiki_page._id in contributor.comments_viewed_timestamp

        # user updates the wiki
        project.update_node_wiki('test', 'Updating wiki', self.auth)
        comment.reload()
        contributor.reload()

        new_version_id = project.get_wiki_version('test')._id
        assert wiki_page._id in contributor.comments_viewed_timestamp
        assert comment.target.referent._id == wiki_page._id

    # Regression test for https://openscience.atlassian.net/browse/OSF-8584
    def test_no_read_more_when_less_than_400_character(self):
        wiki_content = '1234567'
        for x in range(39):
            wiki_content += '1234567890'
        assert len(wiki_content) == 397
        project = ProjectFactory(creator=self.user)
        project.update_node_wiki('home', wiki_content, self.auth)
        res = serialize_wiki_widget(project)
        assert not res['more']

    def test_read_more_when_more_than_400_character(self):
        wiki_content = ''
        for x in range(1000):
            wiki_content += 'a'
        assert len(wiki_content) == 1000
        project = ProjectFactory(creator=self.user)
        project.update_node_wiki('home', wiki_content, self.auth)
        res = serialize_wiki_widget(project)
        assert res['more']


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
        self.wiki_page = self.project.get_wiki_page('home')

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
        page = self.project.get_wiki_version(new_name)
        assert old_name != page.wiki_page.page_name
        assert new_name == page.wiki_page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_case_sensitive(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.project.update_node_wiki(old_name, 'new content', self.auth)
        self.project.rename_node_wiki(old_name, new_name, self.auth)
        new_page = self.project.get_wiki_version(new_name)
        assert new_name == new_page.wiki_page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_existing_deleted_page(self):
        old_name = 'old page'
        new_name = 'new page'
        old_content = 'old content'
        new_content = 'new content'
        # create the old page and delete it
        self.project.update_node_wiki(old_name, old_content, self.auth)
        old_page = self.project.get_wiki_version(old_name)
        assert self.project.get_wiki_page(old_name).deleted is None
        self.project.delete_node_wiki(old_name, self.auth)
        assert self.project.get_wiki_page(old_name) is None
        # create the new page and rename it
        self.project.update_node_wiki(new_name, new_content, self.auth)
        self.project.rename_node_wiki(new_name, old_name, self.auth)
        new_page = self.project.get_wiki_version(old_name)
        # renaming over an existing deleted page just creates a new page with
        # the same name as the deleted page. Page names just need to be unique
        # among non-deleted wikis.
        assert old_content == old_page.content
        assert new_content == new_page.content
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_conflict(self):
        existing_name = 'existing page'
        new_name = 'new page'
        self.project.update_node_wiki(existing_name, 'old content', self.auth)
        assert self.project.get_wiki_page(existing_name).page_name == existing_name
        self.project.update_node_wiki(new_name, 'new content', self.auth)
        assert self.project.get_wiki_page(new_name).page_name == new_name
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
        self.project.update_node_wiki('not home', 'Hello world', self.auth)
        self.wiki_page = self.project.get_wiki_page('not home')

    def test_delete_log(self):
        # Delete wiki
        self.project.delete_node_wiki('not home', self.auth)
        # Deletion is logged
        assert self.project.logs.latest().action == 'wiki_deleted'

    def test_delete_log_specifics(self):
        page = self.project.get_wiki_page('not home')
        self.project.delete_node_wiki('not home', self.auth)
        log = self.project.logs.latest()
        assert 'wiki_deleted' == log.action
        assert page._primary_key == log.params['page_id']

    def test_wiki_versions(self):
        # Number of versions is correct
        assert self.wiki_page.current_version_number == 1
        # Delete wiki
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.project.delete_node_wiki('not home', self.auth)
        # Number of versions is still correct
        self.wiki_page.reload()
        assert self.wiki_page.deleted == mock_now
        assert self.wiki_page.current_version_number == 1
        # get_wiki_page only returns non-deleted wikis
        assert self.project.get_wiki_page('not home') is None

    def test_wiki_delete(self):
        page = self.project.get_wiki_page('not home')
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.project.delete_node_wiki('not home', self.auth)
        # page was deleted
        page.reload()
        assert page.deleted == mock_now
        assert self.project.get_wiki_page('not home') is None

        log = self.project.logs.latest()

        # deletion was logged
        assert log.action == 'wiki_deleted'
        # log date is not set to the page's creation date
        assert log.date > page.created

    def test_deleted_versions(self):
        # Update wiki a second time
        self.project.update_node_wiki('not home', 'Hola mundo', self.auth)
        assert self.project.get_wiki_version('not home', 2).content == 'Hola mundo'
        # Delete wiki
        self.project.delete_node_wiki('not home', self.auth)
        # Check versions
        assert self.project.get_wiki_version('not home', 2) == None
        assert self.project.get_wiki_version('not home', 1) == None
