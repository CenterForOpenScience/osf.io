from nose.tools import *

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory, NodeFactory

from framework.auth.decorators import Auth
from website.util import rubeus


class TestRubeus(DbTestCase):

    def setUp(self):

        super(TestRubeus, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.save()

        self.project.add_addon('s3')
        self.project.creator.add_addon('s3')
        self.node_settings = self.project.get_addon('s3')
        self.user_settings = self.project.creator.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    def test_hgrid_dummy(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
        )

    def test_hgrid_dummy_fail(self):
        node_settings = self.node_settings
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_not_equals(rubeus.build_addon_root(
            node_settings, node_settings.bucket, permissions=permissions), rv)

    def test_hgrid_dummy_overrides(self):
        node_settings = self.node_settings
        node_settings.config.urls = None
        node = self.project
        user = Auth(self.project.creator)
        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {},
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket,
                permissions=permissions, urls={}
            ),
            rv
        )

    def test_hgrid_dummy_node_urls(self):
        node_settings = self.node_settings
        user = Auth(self.project.creator)

        node = self.project
        node_settings.config.urls = {
            'fetch': node.api_url + 's3/hgrid/',
            'upload': node.api_url + 's3/upload/'
        }

        rv = {
            'addon': 's3',
            'iconUrl': node_settings.config.icon_url,
            'name': 'Amazon Simple Storage Service: {0}'.format(
                node_settings.bucket
            ),
            'kind': 'folder',
            'permissions': {
                'view': node.can_view(user),
                'edit': node.can_edit(user) and not node.is_registration,
            },
            'urls': {
                'fetch': node.api_url + 's3/hgrid/',
                'upload': node.api_url + 's3/upload/'
            },
            'accept': {
                'maxSize': node_settings.config.max_file_size,
                'acceptedFiles': node_settings.config.accept_extensions
            },
            'isAddonRoot': True,
            'extra': None
        }
        permissions = {
            'view': node.can_view(user),
            'edit': node.can_edit(user) and not node.is_registration,
        }
        assert_equals(
            rubeus.build_addon_root(
                node_settings, node_settings.bucket, permissions=permissions
            ),
            rv
        )

    def test_create_dummy_private(self):
        user = UserFactory()
        auth = Auth(user=user)
        public = ProjectFactory.build(is_public=True)
        public.add_contributor(user)
        public.save()
        private = ProjectFactory(project=public, is_public=False)
        NodeFactory(project=private)
        collector = rubeus.NodeFileCollector(node=public, auth=auth)

        private_dummy = collector._create_dummy(private)
        assert_false(private_dummy['permissions']['edit'])
        assert_false(private_dummy['permissions']['view'])
        assert_equal(private_dummy['name'], 'Private Component')
        assert_equal(len(private_dummy['children']), 0)

    def test_collect_components_deleted(self):
        node = NodeFactory(creator=self.project.creator, project=self.project)
        node.is_deleted = True
        collector = rubeus.NodeFileCollector(
            self.project, Auth(user=UserFactory())
        )
        nodes = collector._collect_components(self.project)
        assert_equal(len(nodes), 0)
