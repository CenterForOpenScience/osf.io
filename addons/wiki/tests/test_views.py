# -*- coding: utf-8 -*-
"""Views tests for the wiki addon."""
import pytest
import mock
import pytz
import datetime
from django.utils import timezone

from addons.wiki.models import WikiPage, WikiVersion
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
        self.wiki_page = WikiPage.objects.create_for_node(self.project, 'home', 'Hello world', self.auth)

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert WikiVersion.objects.get_for_node(project1, 'home') is None

    def test_default_is_current(self):
        wv = WikiVersion.objects.get_for_node(self.project, 'home')
        assert wv.is_current is True
        self.wiki_page.update(self.user, 'Hello world 2')
        wv = WikiVersion.objects.get_for_node(self.project, 'home')
        assert wv.is_current == True
        assert wv.identifier == 2

        self.wiki_page.update(self.user, 'Hello world 3')
        wv = WikiVersion.objects.get_for_node(self.project, 'home')
        assert wv.is_current == True
        assert wv.identifier == 3

    def test_wiki_content(self):
        # Wiki has correct content
        assert WikiVersion.objects.get_for_node(self.project, 'home').content == 'Hello world'
        # user updates the wiki a second time
        self.wiki_page.update(self.user, 'Hola mundo')
        # Both versions have the expected content
        assert WikiVersion.objects.get_for_node(self.project, 'home', 2).content == 'Hola mundo'
        assert WikiVersion.objects.get_for_node(self.project, 'home', 1).content == 'Hello world'

    def test_current(self):
        # Wiki is current
        assert WikiVersion.objects.get_for_node(self.project, 'home', 1).is_current is True
        # user updates the wiki a second time
        self.wiki_page.update(self.user, 'Hola mundo')
        # New version is current, old version is not
        assert WikiVersion.objects.get_for_node(self.project, 'home', 2).is_current is True
        assert WikiVersion.objects.get_for_node(self.project, 'home', 1).is_current is False

    def test_update_log(self):
        # Updates are logged
        assert self.project.logs.latest().action == 'wiki_updated'
        # user updates the wiki a second time
        self.wiki_page.update(self.user, 'Hola mundo')
        # There are two update logs
        assert self.project.logs.filter(action='wiki_updated').count() == 2

    def test_update_log_specifics(self):
        page = WikiPage.objects.get_for_node(self.project, 'home')
        log = self.project.logs.latest()
        assert 'wiki_updated' == log.action
        assert page._primary_key == log.params['page_id']

    def test_wiki_versions(self):
        # Number of versions is correct
        assert self.wiki_page.current_version_number == 1
        # Update wiki
        self.wiki_page.update(self.user, 'Hello world')
        # Number of versions is correct
        assert self.wiki_page.current_version_number == 2
        # Versions are different
        versions = self.wiki_page.get_versions()
        assert versions[0]._id != versions[1]._id

    def test_update_two_node_wikis(self):
        # user creates a second wiki for the same node
        second_wiki = WikiPage.objects.create_for_node(self.project, 'second', 'Hola mundo', self.auth)
        # each wiki only has one version
        assert self.wiki_page.current_version_number == 1
        assert second_wiki.current_version_number == 1
        # There are 2 logs saved
        assert self.project.logs.filter(action='wiki_updated').count() == 2
        # Each wiki has the expected content
        assert WikiVersion.objects.get_for_node(self.project, 'home').content == 'Hello world'
        assert WikiVersion.objects.get_for_node(self.project, 'second').content == 'Hola mundo'

    @pytest.mark.enable_implicit_clean
    def test_update_name_invalid(self):
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        with pytest.raises(NameInvalidError):
            WikiPage.objects.create_for_node(self.project, invalid_name, 'more valid content', self.auth)

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
        wiki_page.update(self.user, 'Updating wiki')
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
        wiki_page.update(self.user, 'Updating wiki')
        comment.reload()
        contributor.reload()

        new_version_id = WikiVersion.objects.get_for_node(project, 'test')._id
        assert wiki_page._id in contributor.comments_viewed_timestamp
        assert comment.target.referent._id == wiki_page._id

    # Regression test for https://openscience.atlassian.net/browse/OSF-8584
    def test_no_read_more_when_less_than_400_character(self):
        wiki_content = '1234567'
        for x in range(39):
            wiki_content += '1234567890'
        assert len(wiki_content) == 397
        project = ProjectFactory(creator=self.user)
        WikiPage.objects.create_for_node(project, 'home', wiki_content, self.auth)
        res = serialize_wiki_widget(project)
        assert not res['more']

    def test_read_more_when_more_than_400_character(self):
        wiki_content = ''
        for x in range(1000):
            wiki_content += 'a'
        assert len(wiki_content) == 1000
        project = ProjectFactory(creator=self.user)
        WikiPage.objects.create_for_node(project, 'home', wiki_content, self.auth)
        res = serialize_wiki_widget(project)
        assert res['more']


@pytest.mark.enable_implicit_clean
class TestRenameNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestRenameNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates a wiki
        self.wiki_page = WikiPage.objects.create_for_node(self.project, 'home', 'Hello world', self.auth)
        self.name = 'Second wiki'
        self.second_wiki = WikiPage.objects.create_for_node(self.project, self.name, 'some content', self.auth)

    def test_rename_new_name_invalid_none_or_blank(self):
        name = 'New Page'
        for invalid_name in [None, '', '   ']:
            with pytest.raises(ValidationError):
                self.second_wiki.rename(invalid_name, self.auth)

    def test_rename_new_name_invalid_special_characters(self):
        # forward slashes are not allowed
        invalid_name = 'invalid/name'
        with pytest.raises(NameInvalidError):
            self.second_wiki.rename(invalid_name, self.auth)

    def test_rename_name_maximum_length(self):
        new_name = 'a' * 101
        with pytest.raises(NameMaximumLengthError):
            self.second_wiki.rename(new_name, self.auth)

    def test_rename_cannot_rename(self):
        with pytest.raises(PageCannotRenameError):
            wp = WikiPage.objects.get_for_node(self.project, 'home')
            wp.rename('New Home', self.auth)

        with pytest.raises(PageCannotRenameError):
            wp = WikiPage.objects.get_for_node(self.project, 'HOME')
            wp.rename('New Home', self.auth)

    def test_rename_page_not_found(self):
        wp = WikiPage.objects.get_for_node(self.project, 'abc123')
        wp = WikiPage.objects.get_for_node(self.project, u'ˆ•¶£˙˙®¬™∆˙')

    def test_rename_page(self):
        new_name = 'New pAGE'
        self.second_wiki.rename(new_name, self.auth)
        page = WikiVersion.objects.get_for_node(self.project, new_name)
        assert self.name != page.wiki_page.page_name
        assert new_name == page.wiki_page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_case_sensitive(self):
        old_name = 'new page'
        new_name = 'New pAGE'
        self.second_wiki.rename(new_name, self.auth)
        new_page = WikiVersion.objects.get_for_node(self.project, new_name)
        assert new_name == new_page.wiki_page.page_name
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_existing_deleted_page(self):
        old_name = 'old page'
        new_name = 'new page'
        old_content = 'old content'
        new_content = 'new content'
        # create the old page and delete it
        old_page = WikiPage.objects.create_for_node(self.project, old_name, old_content, self.auth)
        old_version = old_page.get_version()
        assert WikiPage.objects.get_for_node(self.project, old_name).deleted is None
        old_page.delete(self.auth)
        assert WikiPage.objects.get_for_node(self.project, 'old_name') is None
        # create the new page and rename it
        new_page = WikiPage.objects.create_for_node(self.project, new_name, new_content, self.auth)
        new_version = new_page.get_version()
        new_page.rename(old_name, self.auth)
        new_page = WikiVersion.objects.get_for_node(self.project, old_name)
        # renaming over an existing deleted page just creates a new page with
        # the same name as the deleted page. Page names just need to be unique
        # among non-deleted wikis.
        assert old_content == old_version.content
        assert new_content == new_version.content
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_page_conflict(self):
        existing_name = 'existing page'
        new_name = 'new page'
        old_page = WikiPage.objects.create_for_node(self.project, existing_name, 'some content', self.auth)
        assert WikiPage.objects.get_for_node(self.project, existing_name).page_name == existing_name
        new_page = WikiPage.objects.create_for_node(self.project, new_name, 'new content', self.auth)
        assert WikiPage.objects.get_for_node(self.project, new_name).page_name == new_name
        with pytest.raises(PageConflictError):
            new_page.rename(existing_name, self.auth)

    def test_rename_log(self):
        # Rename wiki
        wp = WikiPage.objects.create_for_node(self.project, 'wiki', 'content', self.auth)
        wp.rename('renamed_wiki', self.auth)

        # Rename is logged
        assert self.project.logs.latest().action == 'wiki_renamed'

    def test_rename_log_specifics(self):
        wp = WikiPage.objects.create_for_node(self.project, 'wiki', 'content', self.auth)
        wp.rename('renamed_wiki', self.auth)

        log = self.project.logs.latest()
        assert 'wiki_renamed' == log.action
        assert wp._primary_key == log.params['page_id']


class TestDeleteNodeWiki(OsfTestCase):

    def setUp(self):
        super(TestDeleteNodeWiki, self).setUp()
        # Create project with component
        self.user = UserFactory()
        self.auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, parent=self.project)
        # user updates the wiki
        self.wiki_page = WikiPage.objects.create_for_node(self.project, 'not home', 'Hello world', self.auth)

    def test_delete_log(self):
        # Delete wiki
        self.wiki_page.delete(self.auth)
        # Deletion is logged
        assert self.project.logs.latest().action == 'wiki_deleted'

    def test_delete_log_specifics(self):
        self.wiki_page.delete(self.auth)
        log = self.project.logs.latest()
        assert 'wiki_deleted' == log.action
        assert self.wiki_page._primary_key == log.params['page_id']

    def test_wiki_versions(self):
        # Number of versions is correct
        assert self.wiki_page.current_version_number == 1
        # Delete wiki
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.wiki_page.delete(self.auth)
        # Number of versions is still correct
        self.wiki_page.reload()
        assert self.wiki_page.deleted == mock_now
        assert self.wiki_page.current_version_number == 1
        # WikiPage.objects.get_for_node(...) only returns non-deleted wikis
        assert WikiPage.objects.get_for_node(self.project, 'not home') is None

    def test_wiki_delete(self):
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.wiki_page.delete(self.auth)
        # page was deleted
        self.wiki_page.reload()
        assert self.wiki_page.deleted == mock_now
        assert WikiPage.objects.get_for_node(self.project, 'not home') is None

        log = self.project.logs.latest()

        # deletion was logged
        assert log.action == 'wiki_deleted'
        # log date is not set to the page's creation date
        assert log.date > self.wiki_page.created

    def test_deleted_versions(self):
        # Update wiki a second time
        self.wiki_page.update(self.user, 'Hola mundo')
        assert WikiVersion.objects.get_for_node(self.project, 'not home', 2).content == 'Hola mundo'
        # Delete wiki
        self.wiki_page.delete(self.auth)
        # Check versions
        assert WikiVersion.objects.get_for_node(self.project, 'not home', 2) == None
        assert WikiVersion.objects.get_for_node(self.project, 'not home', 1) == None
