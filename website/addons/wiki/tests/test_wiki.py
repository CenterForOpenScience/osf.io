# -*- coding: utf-8 -*-

# PEP8 asserts
from nose.tools import *  # noqa
from webtest.app import AppError
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website.addons.wiki.views import serialize_wiki_toc
from website.addons.wiki.model import NodeWikiPage
from framework.auth import Auth

class TestNodeWikiPageModel(OsfTestCase):

    def test_page_name_cannot_be_greater_than_100_characters(self):
        bad_name = 'a' * 101
        page = NodeWikiPage(page_name=bad_name)
        with assert_raises(ValidationValueError):
            page.save()


class TestWikiViews(OsfTestCase):

    def setUp(self):
        super(TestWikiViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)

    def test_wiki_url_get_returns_200(self):
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_pointer_returns_200(self):
        pointer = PointerFactory(node=self.project)
        url = self.project.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    def test_wiki_content_returns_200(self):
        node = ProjectFactory()
        url = node.api_url_for('wiki_page_content', wid='somerandomid')
        res = self.app.get(url).follow()
        assert_equal(res.status_code, 200)

    def test_wiki_url_for_component_returns_200(self):
        component = NodeFactory(project=self.project)
        url = component.web_url_for('project_wiki_page', wid='home')
        res = self.app.get(url).follow()
        assert_equal(res.status_code, 200)

    def test_serialize_wiki_toc(self):
        project = ProjectFactory()
        auth = Auth(project.creator)
        NodeFactory(project=project, creator=project.creator)
        no_wiki = NodeFactory(project=project, creator=project.creator)
        project.save()

        serialized = serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 2)
        no_wiki.delete_addon('wiki', auth=auth)
        serialized = serialize_wiki_toc(project, auth=auth)
        assert_equal(len(serialized), 1)

    def test_get_wiki_url_pointer_component(self):
        """Regression test for issues
        https://github.com/CenterForOpenScience/osf/issues/363 and
        https://github.com/CenterForOpenScience/openscienceframework.org/issues/574

        """
        user = UserFactory()
        pointed_node = NodeFactory(creator=user)
        project = ProjectFactory(creator=user)
        auth = Auth(user=user)
        project.add_pointer(pointed_node, auth=auth, save=True)

        serialized = serialize_wiki_toc(project, auth)
        assert_equal(
            serialized[0]['url'],
            pointed_node.web_url_for('project_wiki_page', wid='home')
        )

    def test_project_wiki_edit_post(self):
        self.project.update_node_wiki(
            'home',
            content='old content',
            auth=Auth(self.project.creator)
        )
        url = self.project.web_url_for('project_wiki_edit_post', wid='home')
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        # page was updated with new content
        new_wiki = self.project.get_wiki_page('home')
        assert_equal(new_wiki.content, 'new content')

    def test_project_wiki_edit_post_with_non_ascii_title(self):
        # regression test for https://github.com/CenterForOpenScience/openscienceframework.org/issues/1040
        # wid doesn't exist in the db, so it will be created
        new_wid = u'øˆ∆´ƒøßå√ß'
        url = self.project.web_url_for('project_wiki_edit_post', wid=new_wid)
        res = self.app.post(url, {'content': 'new content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)
        self.project.reload()
        wiki = self.project.get_wiki_page(new_wid)
        assert_equal(wiki.page_name, new_wid)

        # updating content should return correct url as well.
        res = self.app.post(url, {'content': 'updated content'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_new(self):
        url = self.project.web_url_for('project_wiki_edit', wid='a new page')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_wiki_edit_get_home(self):
        url = self.project.web_url_for('project_wiki_edit', wid='home')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

class TestWikiDelete(OsfTestCase):

    def setUp(self):
        super(TestWikiDelete, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('Elephants', 'Hello Elephants', self.consolidate_auth)
        self.project.update_node_wiki('Lions', 'Hello Lions', self.consolidate_auth)
        self.elephant_wiki = self.project.get_wiki_page('Elephants')
        self.lion_wiki = self.project.get_wiki_page('Lions')
        self.url = self.project.api_url_for(
            'project_wiki_delete',
            wid=self.elephant_wiki._id
        )

    def test_project_wiki_delete(self):
        assert 'elephants' in self.project.wiki_pages_current
        self.app.delete(
            self.url,
            auth=self.auth
        )
        self.project.reload()
        assert 'elephants' not in self.project.wiki_pages_current


class TestWikiRename(OsfTestCase):

    def setUp(self):

        super(TestWikiRename, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('home', 'Hello world', self.consolidate_auth)
        self.wiki = self.project.get_wiki_page('home')
        self.url = self.project.api_url_for(
            'project_wiki_rename',
            wid=self.wiki._id,
        )

    def test_rename_wiki_page_valid(self):
        new_name = 'away'
        self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.wiki._id},
            auth=self.auth,
        )
        self.project.reload()

        old_wiki = self.project.get_wiki_page('home')
        assert_false(old_wiki)

        new_wiki = self.project.get_wiki_page(new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki._id, self.wiki._id)
        assert_equal(new_wiki.content, self.wiki.content)
        assert_equal(new_wiki.version, self.wiki.version)

    def test_rename_wiki_page_invalid(self):
        new_name = '<html>hello</html>'

        with assert_raises(AppError) as cm:
            self.app.put_json(self.url, {'value': new_name, 'pk': self.wiki._id}, auth=self.auth)

            e = cm.exception
            assert_equal(e, 422)

    def test_rename_wiki_page_duplicate(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'away'

        with assert_raises(AppError) as cm:
            self.app.put_json(
                self.url,
                {'value': new_name, 'pk': self.wiki._id},
                auth=self.auth,
            )

            e = cm.exception
            assert_equal(e, 409)


class TestWikiLinks(OsfTestCase):

    def test_links(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        wiki = NodeWikiFactory(
            content='[[wiki2]]',
            user=user,
            node=project,
        )
        assert_in(
            project.web_url_for('project_wiki_page', wid='wiki2'),
            wiki.html(project),
        )
