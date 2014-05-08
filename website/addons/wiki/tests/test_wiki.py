# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts

import framework
from framework.auth.decorators import Auth
from website.app import init_app
from webtest_plus import TestApp
from tests.base import OsfTestCase
from tests.factories import (
    UserFactory, NodeFactory, PointerFactory, ProjectFactory
)

from website.addons.wiki.views import get_wiki_url, serialize_wiki_toc

app = init_app(routes=True, set_backends=False)


class TestWikiViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.project = ProjectFactory(is_public=True)

    def test_get_wiki_url_for_project(self):
        with app.test_request_context():
            node = ProjectFactory()
            expected = framework.url_for(
                'OsfWebRenderer__project_wiki_page',
                pid=node._primary_key,
                wid='home')
            assert_equal(get_wiki_url(node), expected)

    def test_wiki_url_get_returns_200(self):
        with app.test_request_context():
            url = get_wiki_url(self.project)
            res = self.app.get(url)
            assert_equal(res.status_code, 200)

    def test_wiki_url_for_pointer_returns_200(self):
        with app.test_request_context():
            pointer = PointerFactory(node=self.project)
            url = get_wiki_url(pointer)
            res = self.app.get(url)
            assert_equal(res.status_code, 200)

    def test_wiki_url_for_component_returns_200(self):
        with app.test_request_context():
            component = NodeFactory(project=self.project)
            url = get_wiki_url(component)
            res = self.app.get(url).follow()
            assert_equal(res.status_code, 200)

    def test_serialize_wiki_toc(self):
        project = ProjectFactory()
        auth = Auth(project.creator)
        has_wiki = NodeFactory(project=project, creator=project.creator)
        no_wiki = NodeFactory(project=project, creator=project.creator)
        project.save()
        with app.test_request_context():
            serialized = serialize_wiki_toc(project, auth=auth)
            assert_equal(len(serialized), 2)
            no_wiki.delete_addon('wiki', auth=auth)
            serialized = serialize_wiki_toc(project, auth=auth)
            assert_equal(len(serialized), 1)

    def test_get_wiki_url_pointer_component(self):
        """Regression test for issue
        https://github.com/CenterForOpenScience/osf/issues/363

        """
        user = UserFactory()
        pointed_node = NodeFactory(creator=user)
        project = ProjectFactory(creator=user)
        auth = Auth(user=user)
        project.add_pointer(pointed_node, auth=auth, save=True)

        with app.test_request_context():
            serialize_wiki_toc(project, auth)
