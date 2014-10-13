# -*- coding: utf-8 -*-

# PEP8 asserts
import httplib as http
import uuid

from nose.tools import *  # noqa
from modularodm.exceptions import ValidationValueError

from tests.base import OsfTestCase, fake
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory, ApiKeyFactory,
    AuthUserFactory, NodeWikiFactory,
)

from website.addons.wiki.views import serialize_wiki_toc
from website.addons.wiki.model import NodeWikiPage
from website.addons.wiki.utils import docs_uuid, generate_share_uuid
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


    def test_project_wiki_edit_post_with_new_wid_and_no_content(self):
        page_name = fake.catch_phrase()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': ''}, auth=self.user.auth).follow()

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
        assert_is_not_none(new_page)


    def test_project_wiki_edit_post_with_new_wid_and_content(self):
        page_name, page_content = fake.catch_phrase(), fake.bs()

        old_wiki_page_count = NodeWikiPage.find().count()
        url = self.project.web_url_for('project_wiki_edit_post', wid=page_name)
        # User submits to edit form with no content
        res = self.app.post(url, {'content': page_content}, auth=self.user.auth).follow()

        new_wiki_page_count = NodeWikiPage.find().count()
        # A new wiki page was created in the db
        assert_equal(new_wiki_page_count, old_wiki_page_count + 1)

        # Node now has the new wiki page associated with it
        self.project.reload()
        new_page = self.project.get_wiki_page(page_name)
        assert_is_not_none(new_page)
        # content was set
        assert_equal(new_page.content, page_content)

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

    def test_project_wiki_compare_returns_200(self):
        self.project.update_node_wiki('home', 'updated content', Auth(self.user))
        self.project.save()
        url = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_project_wiki_compare_with_invalid_wid(self):
        url = self.project.web_url_for('project_wiki_compare', wid='this-doesnt-exist', compare_id=1)
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_wiki_page_creation_strips_whitespace(self):
        # Regression test for:
        # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1080
        # wid has a trailing space
        url = self.project.web_url_for('project_wiki_edit', wid='cupcake ')
        res = self.app.post(url, {'content': 'blah'}, auth=self.user.auth).follow()
        assert_equal(res.status_code, 200)

        self.project.reload()
        wiki = self.project.get_wiki_page('cupcake')
        assert_is_not_none(wiki)


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

    def test_project_wiki_delete(self):
        assert 'elephants' in self.project.wiki_pages_current
        url = self.project.api_url_for(
            'project_wiki_delete',
            wid='elephants'
        )
        self.app.delete(
            url,
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

        self.page_name = 'page2'
        self.project.update_node_wiki(self.page_name, 'content', self.consolidate_auth)
        self.project.save()
        self.page = self.project.get_wiki_page(self.page_name)

        self.wiki = self.project.get_wiki_page('home')
        self.url = self.project.api_url_for(
            'project_wiki_rename',
            wid=self.wiki._id,
        )

    def test_rename_wiki_page_valid(self):
        new_name = 'away'
        self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
        )
        self.project.reload()

        old_wiki = self.project.get_wiki_page(self.page_name)
        assert_false(old_wiki)

        new_wiki = self.project.get_wiki_page(new_name)
        assert_true(new_wiki)
        assert_equal(new_wiki._id, self.page._id)
        assert_equal(new_wiki.content, self.page.content)
        assert_equal(new_wiki.version, self.page.version)

    def test_rename_wiki_page_invalid(self):
        new_name = '<html>hello</html>'

        res = self.app.put_json(self.url, {'value': new_name, 'pk': self.page._id},
                auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 422)

    def test_rename_wiki_page_duplicate(self):
        self.project.update_node_wiki('away', 'Hello world', self.consolidate_auth)
        new_name = 'away'

        res = self.app.put_json(
            self.url,
            {'value': new_name, 'pk': self.page._id},
            auth=self.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 409)

    def test_cannot_rename_home_page(self):
        home = self.project.get_wiki_page('home')
        res = self.app.put_json(self.url, {'value': 'homelol', 'pk': home._id}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_can_rename_to_a_deleted_page(self):
        self.project.delete_node_wiki(self.project, self.page, self.consolidate_auth)
        self.project.save()

        # Creates a new page
        self.project.update_node_wiki('page3' ,'moarcontent', self.consolidate_auth)
        page3 = self.project.get_wiki_page('page3')
        self.project.save()

        url = self.project.api_url_for('project_wiki_rename', wid='page3')
        # Renames the wiki to the deleted page
        res = self.app.put_json(self.url, {'value': self.page_name, 'pk': page3._id}, auth=self.auth)
        assert_equal(res.status_code, 200)


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


class TestWikiCompare(OsfTestCase):

    def setUp(self):
        super(TestWikiCompare, self).setUp()

        self.project = ProjectFactory(is_public=True)
        api_key = ApiKeyFactory()
        self.project.creator.api_keys.append(api_key)
        self.project.creator.save()
        self.consolidate_auth = Auth(user=self.project.creator, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.project.update_node_wiki('home', 'hello world', self.consolidate_auth)
        self.wiki = self.project.get_wiki_page('home')

    def test_compare_wiki_page_valid(self):
        self.project.update_node_wiki('home', 'Hello World', self.consolidate_auth)

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url_v1_to_v2)
        comparison_v1_to_v2 = \
            '<span style="background:#D16587; font-size:1.5em;">h</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">H</span>ello ' \
            '<span style="background:#D16587; font-size:1.5em;">w</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">W</span>orld'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v1_to_v2 in res.body)

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = 'Hello World'
        assert_equal(res.status_int, http.OK)
        assert_true(comparison_v2_to_v2 in res.body)

    def test_compare_wiki_page_sanitized(self):
        content_js_script = '<script>alert(''a problem'');</script>'
        self.project.update_node_wiki('home', content_js_script, self.consolidate_auth)

        url_v1_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=1)
        res = self.app.get(url_v1_to_v2)
        comparison_v1_to_v2 = \
            '<span style="background:#D16587; font-size:1.5em;">h</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">&lt;script&gt;al</span>e' \
            '<span style="background:#4AA02C; font-size:1.5em; ">rt(''a prob</span>l' \
            '<span style="background:#D16587; font-size:1.5em;">lo wo</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">em'');</span>r' \
            '<span style="background:#D16587; font-size:1.5em;">ld</span>' \
            '<span style="background:#4AA02C; font-size:1.5em; ">ipt&gt;</span>'
        assert_equal(res.status_int, http.OK)
        assert_true(content_js_script not in res.body)
        assert_true(comparison_v1_to_v2 in res.body)

        url_v2_to_v2 = self.project.web_url_for('project_wiki_compare', wid='home', compare_id=2)
        res = self.app.get(url_v2_to_v2)
        comparison_v2_to_v2 = '&lt;script&gt;alert(''a problem'');&lt;/script&gt;'
        assert_equal(res.status_int, http.OK)
        assert_true(content_js_script not in res.body)
        assert_true(comparison_v2_to_v2 in res.body)


class TestWikiShareJS(OsfTestCase):

    def setUp(self):
        super(TestWikiShareJS, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)

    def test_uuid_generated(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))
        url = self.project.web_url_for('project_wiki_edit', wid=wid)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)

        self.project.reload()
        assert_true(self.project.wiki_sharejs_uuids.get(wid))
        assert_not_in(self.project.wiki_sharejs_uuids.get(wid), res.body)
        assert_in(docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid)), res.body)

    def test_uuids_differ_between_pages(self):
        wid1 = 'foo'
        url1 = self.project.web_url_for('project_wiki_edit', wid=wid1)
        res1 = self.app.get(url1, auth=self.user.auth)
        assert_equal(res1.status_code, 200)

        wid2 = 'bar'
        url2 = self.project.web_url_for('project_wiki_edit', wid=wid2)
        res2 = self.app.get(url2, auth=self.user.auth)
        assert_equal(res2.status_code, 200)

        self.project.reload()
        uuid1 = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid1))
        uuid2 = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid2))

        assert_not_equal(uuid1, uuid2)
        assert_in(uuid1, res1)
        assert_in(uuid2, res2)
        assert_not_in(uuid1, res2)
        assert_not_in(uuid2, res1)

    def test_uuids_differ_between_forks(self):
        wid = 'foo'
        url = self.project.web_url_for('project_wiki_edit', wid=wid)
        project_res = self.app.get(url, auth=self.user.auth)
        assert_equal(project_res.status_code, 200)
        self.project.reload()

        fork = self.project.fork_node(Auth(self.user))
        assert_true(fork.is_fork_of(self.project))
        fork_url = fork.web_url_for('project_wiki_edit', wid=wid)
        fork_res = self.app.get(fork_url, auth=self.user.auth)
        assert_equal(fork_res.status_code, 200)
        fork.reload()

        # uuids are stored the same internally
        assert_equal(
            self.project.wiki_sharejs_uuids.get(wid),
            fork.wiki_sharejs_uuids.get(wid)
        )

        project_uuid = docs_uuid(self.project, self.project.wiki_sharejs_uuids.get(wid))
        fork_uuid = docs_uuid(fork, fork.wiki_sharejs_uuids.get(wid))

        assert_not_equal(project_uuid, fork_uuid)
        assert_in(project_uuid, project_res)
        assert_in(fork_uuid, fork_res)
        assert_not_in(project_uuid, fork_res)
        assert_not_in(fork_uuid, project_res)

    def test_uuid_persists_after_delete(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))

        # Visit wiki edit page
        edit_url = self.project.web_url_for('project_wiki_edit', wid=wid)
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        old_id = self.project.wiki_sharejs_uuids.get(wid)

        # Delete wiki
        delete_url = self.project.api_url_for('project_wiki_delete', wid=wid)
        res = self.app.get(delete_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(old_id, self.project.wiki_sharejs_uuids.get(wid))

        # Revisit wiki edit page
        res = self.app.get(edit_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(old_id, self.project.wiki_sharejs_uuids.get(wid))
        assert_in(docs_uuid(self.project, old_id), res.body)


class TestWikiUtils(OsfTestCase):

    def setUp(self):
        super(TestWikiUtils, self).setUp()
        self.project = ProjectFactory()

    def test_docs_uuid(self):
        share_uuid = str(uuid.uuid1())

        # Provides consistent results
        assert_equal(docs_uuid(self.project, share_uuid), docs_uuid(self.project, share_uuid))

        # Provides obfuscation
        assert_not_in(share_uuid, docs_uuid(self.project, share_uuid))
        assert_not_in(docs_uuid(self.project, share_uuid), share_uuid)

        # Differs based on share uuid provided
        assert_not_equal(docs_uuid(self.project, share_uuid), self.project, str(uuid.uuid1()))

        # Differs across projects and forks
        project = ProjectFactory()
        fork = self.project.fork_node(Auth(self.project.creator))
        assert_not_equal(docs_uuid(self.project, share_uuid), docs_uuid(project, share_uuid))
        assert_not_equal(docs_uuid(self.project, share_uuid), docs_uuid(fork, share_uuid))

    def test_generate_share_uuid(self):
        wid = 'foo'
        assert_is_none(self.project.wiki_sharejs_uuids.get(wid))
        share_uuid = generate_share_uuid(self.project, wid)
        self.project.reload()
        assert_equal(self.project.wiki_sharejs_uuids[wid], share_uuid)

        new_uuid = generate_share_uuid(self.project, wid)
        self.project.reload()
        assert_not_equal(share_uuid, new_uuid)
        assert_equal(self.project.wiki_sharejs_uuids[wid], new_uuid)
