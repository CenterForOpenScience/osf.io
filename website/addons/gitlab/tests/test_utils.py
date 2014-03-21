import unittest
from nose.tools import *

import os

from website.addons.gitlab.tests import GitlabTestCase

from website.addons.gitlab import utils


class TestTranslatePermissions(unittest.TestCase):

    def test_translate_admin(self):
        assert_equal(
            utils.translate_permissions(['read', 'write', 'admin']),
            'master'
        )

    def test_translate_write(self):
        assert_equal(
            utils.translate_permissions(['read', 'write']),
            'developer'
        )

    def test_translate_read(self):
        assert_equal(
            utils.translate_permissions(['read']),
            'reporter'
        )


class TestKwargsToPath(unittest.TestCase):

    pass


class TestRefsToParams(unittest.TestCase):

    pass


class TestSlugify(unittest.TestCase):

    def test_replace_special(self):
        assert_equal(
            utils.gitlab_slugify('foo&bar_baz'),
            'foo-bar-baz'
        )

    def test_replace_git(self):
        assert_equal(
            utils.gitlab_slugify('foo.git'),
            'foo'
        )


class TestTypeToKind(unittest.TestCase):

    def test_blob(self):
        pass

    def test_tree(self):
        pass


class TestBuildUrls(GitlabTestCase):

    def test_tree(self):

        item = {
            'name': 'foo',
            'type': 'tree',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_urls(
            self.project, item, path, branch, sha
        )

        assert_equal(
            set(output.keys()),
            {'upload', 'fetch'}
        )
        assert_equal(
            output['upload'],
            os.path.join(
                self.project.api_url, 'gitlab', 'files', path
            ) + '/?branch=master'
        )
        assert_equal(
            output['fetch'],
            os.path.join(
                self.project.api_url, 'gitlab', 'grid', path
            ) + '/?branch=master&sha=12345'
        )

    def test_blob(self):

        item = {
            'name': 'bar',
            'type': 'blob',
        }
        path = 'myfolder'
        branch = 'master'
        sha = '12345'

        output = utils.build_urls(
            self.project, item, path, branch, sha
        )

        assert_equal(
            set(output.keys()),
            {'view', 'download', 'delete'}
        )
        assert_equal(
            output['view'],
            os.path.join(
                self.project.url, 'gitlab', 'files', path
            ) + '?branch=master&sha=12345'
        )
        assert_equal(
            output['download'],
            os.path.join(
                self.project.url, 'gitlab', 'files', path, 'download'
            ) + '?branch=master&sha=12345'
        )
        assert_equal(
            output['delete'],
            os.path.join(
                self.project.api_url, 'gitlab', 'files', path
            ) + '?branch=master'
        )

    def test_bad_type(self):
        with assert_raises(ValueError):
            utils.build_urls(
                self.project, item={}, path=''
            )


class TestGridSerializers(GitlabTestCase):

    def test_item_to_hgrid(self):

        item = {
            'name': 'myfile',
            'type': 'blob',
        }
        path = 'myfolder'
        permissions = {
            'view': True,
            'edit': True,
        }

        output = utils.item_to_hgrid(
            self.project, item, path, permissions
        )

        assert_equal(output['name'], 'myfile')
        assert_equal(output['kind'], utils.type_to_kind['blob'])
        assert_equal(output['permissions'], permissions)
        assert_equal(
            output['urls'],
            utils.build_urls(
                self.project, item, os.path.join(path, item['name'])
            )
        )
