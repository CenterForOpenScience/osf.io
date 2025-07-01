from unittest import mock
import pytest

from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.base.settings import API_BASE
from framework.auth import Auth
from osf.utils.permissions import READ
from osf_tests.factories import InstitutionFactory, AuthUserFactory, ProjectFactory, RegistrationFactory, NodeFactory


@pytest.mark.django_db
class NodeCRUDTestCase:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_two(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_two(self, institution_one, institution_two):
        auth_user = AuthUserFactory()
        auth_user.add_or_update_affiliated_institution(institution_one)
        auth_user.add_or_update_affiliated_institution(institution_two)
        return auth_user

    @pytest.fixture()
    def title(self):
        return 'Cool Project'

    @pytest.fixture()
    def title_new(self):
        return 'Super Cool Project'

    @pytest.fixture()
    def description(self):
        return 'A Properly Cool Project'

    @pytest.fixture()
    def description_new(self):
        return 'An even cooler project'

    @pytest.fixture()
    def category(self):
        return 'data'

    @pytest.fixture()
    def category_new(self):
        return 'project'

    @pytest.fixture()
    def project_public(self, user, title, description, category):
        project = ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=True,
            creator=user
        )
        from api.caching import settings as cache_settings
        from api.caching.utils import storage_usage_cache
        from website.settings.defaults import STORAGE_USAGE_CACHE_TIMEOUT

        # Sets public project storage cache to avoid need for retries in tests
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project._id)
        storage_usage_cache.set(key, 0, STORAGE_USAGE_CACHE_TIMEOUT)
        return project

    @pytest.fixture()
    def project_private(self, user, title, description, category):
        return ProjectFactory(
            title=title,
            description=description,
            category=category,
            is_public=False,
            creator=user
        )

    @pytest.fixture()
    def wiki_private(self, user, project_private):
        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki_page = WikiFactory(page_name='foo', node=project_private, user=user)
            WikiVersionFactory(wiki_page=wiki_page)
        return wiki_page

    @pytest.fixture()
    def url_public(self, project_public):
        return f'/{API_BASE}nodes/{project_public._id}/'

    @pytest.fixture()
    def url_private(self, project_private):
        return f'/{API_BASE}nodes/{project_private._id}/'

    @pytest.fixture()
    def url_fake(self):
        return '/{}nodes/{}/'.format(API_BASE, '12345')

    @pytest.fixture()
    def make_node_payload(self):
        def payload(node, attributes, relationships=None):

            payload_data = {
                'data': {
                    'id': node._id,
                    'type': 'nodes',
                    'attributes': attributes,
                }
            }

            if relationships:
                payload_data['data']['relationships'] = relationships

            return payload_data
        return payload


@pytest.mark.django_db
class LinkedRegistrationsTestCase:

    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory(is_public=True)

    @pytest.fixture()
    def node_public(self, registration):
        node_public = NodeFactory(is_public=True)
        node_public.add_pointer(
            registration,
            auth=Auth(node_public.creator)
        )
        node_public.save()
        return node_public

    @pytest.fixture()
    def node_private(self, user_admin_contrib, user_write_contrib, user_read_contrib, registration):
        node_private = NodeFactory(creator=user_admin_contrib)
        node_private.add_contributor(
            user_write_contrib,
            auth=Auth(user_admin_contrib)
        )
        node_private.add_contributor(
            user_read_contrib,
            permissions=READ,
            auth=Auth(user_admin_contrib)
        )
        node_private.add_pointer(
            registration,
            auth=Auth(user_admin_contrib)
        )
        return node_private
