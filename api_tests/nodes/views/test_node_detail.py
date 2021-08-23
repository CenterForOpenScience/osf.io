# -*- coding: utf-8 -*-
import mock
import pytest
from future.moves.urllib.parse import urlparse
from nose.tools import *  # noqa:


from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.base.settings.defaults import API_BASE
from api.caching import settings as cache_settings
from api.caching.utils import storage_usage_cache
from api.taxonomies.serializers import subjects_as_relationships_version
from api_tests.subjects.mixins import UpdateSubjectsMixin
from framework.auth.core import Auth
from osf.models import NodeLog
from osf.models.licenses import NodeLicense
from osf.utils.sanitize import strip_html
from osf.utils import permissions
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    NodeLicenseRecordFactory,
    PrivateLinkFactory,
    PreprintFactory,
    IdentifierFactory,
    InstitutionFactory,
    ForkFactory,
    OSFGroupFactory,
    WithdrawnRegistrationFactory,
    DraftNodeFactory,
)
from rest_framework import exceptions
from tests.base import fake
from tests.utils import assert_latest_log, assert_latest_log_not
from website.views import find_bookmark_collection
from website import settings


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeDetail:

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user):
        return ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def draft_node(self, user):
        return DraftNodeFactory(creator=user)

    @pytest.fixture()
    def project_private(self, user):
        return ProjectFactory(
            title='Project Two',
            is_public=False,
            creator=user)

    @pytest.fixture()
    def component_public(self, user, project_public):
        return NodeFactory(parent=project_public, creator=user, is_public=True)

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/'.format(API_BASE, project_private._id)

    @pytest.fixture()
    def url_component_public(self, component_public):
        return '/{}nodes/{}/'.format(API_BASE, component_public._id)

    @pytest.fixture()
    def permissions_read(self):
        return [permissions.READ]

    @pytest.fixture()
    def permissions_write(self):
        return [permissions.WRITE, permissions.READ]

    @pytest.fixture()
    def permissions_admin(self):
        return [permissions.READ, permissions.ADMIN, permissions.WRITE]

    def test_return_project_details(
            self, app, user, user_two, project_public,
            project_private, url_public, url_private,
            permissions_read, permissions_admin, draft_node):

        #   test_return_public_project_details_logged_out
        res = app.get(url_public)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == project_public.title
        assert res.json['data']['attributes']['description'] == project_public.description
        assert res.json['data']['attributes']['category'] == project_public.category
        assert res.json['data']['attributes']['current_user_is_contributor'] is False
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.READ]

    #   test_return_public_project_details_contributor_logged_in
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == project_public.title
        assert res.json['data']['attributes']['description'] == project_public.description
        assert res.json['data']['attributes']['category'] == project_public.category
        assert res.json['data']['attributes']['current_user_is_contributor'] is True
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.ADMIN, permissions.WRITE, permissions.READ]

    #   test_return_public_project_details_non_contributor_logged_in
        res = app.get(url_public, auth=user_two.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == project_public.title
        assert res.json['data']['attributes']['description'] == project_public.description
        assert res.json['data']['attributes']['category'] == project_public.category
        assert res.json['data']['attributes']['current_user_is_contributor'] is False
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.READ]

    #   test_return_private_project_details_logged_in_admin_contributor
        res = app.get(url_private, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == project_private.title
        assert res.json['data']['attributes']['description'] == project_private.description
        assert res.json['data']['attributes']['category'] == project_private.category
        assert res.json['data']['attributes']['current_user_is_contributor'] is True
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.ADMIN, permissions.WRITE, permissions.READ]
        assert res.json['data']['relationships']['region']['data']['id'] == project_private.osfstorage_region._id

    #   test_return_private_project_details_logged_out
        res = app.get(url_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_project_details_logged_in_non_contributor
        res = app.get(url_private, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_return_project_where_you_have_osf_group_membership
        osf_group = OSFGroupFactory(creator=user_two)
        project_private.add_osf_group(osf_group, permissions.WRITE)
        res = app.get(url_private, auth=user_two.auth)
        assert res.status_code == 200
        assert project_private.has_permission(user_two, permissions.WRITE) is True

    #   test_draft_node_not_returned_under_node_detail_endpoint
        draft_node_url = '/{}nodes/{}/'.format(API_BASE, draft_node._id)
        res = app.get(draft_node_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_return_private_project_details_logged_in_write_contributor(
            self, app, user, user_two, project_private, url_private, permissions_write):
        project_private.add_contributor(
            contributor=user_two, auth=Auth(user), save=True)
        res = app.get(url_private, auth=user_two.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == project_private.title
        assert res.json['data']['attributes']['description'] == project_private.description
        assert res.json['data']['attributes']['category'] == project_private.category
        assert res.json['data']['attributes']['current_user_is_contributor'] is True
        assert_equals(
            res.json['data']['attributes']['current_user_permissions'],
            permissions_write)

    def test_top_level_project_has_no_parent(self, app, url_public):
        res = app.get(url_public)
        assert res.status_code == 200
        assert 'parent' not in res.json['data']['relationships']
        assert 'id' in res.json['data']
        assert res.content_type == 'application/vnd.api+json'

    def test_child_project_has_parent(
            self, app, user, project_public, url_public):
        public_component = NodeFactory(
            parent=project_public, creator=user, is_public=True)
        public_component_url = '/{}nodes/{}/'.format(
            API_BASE, public_component._id)
        res = app.get(public_component_url)
        assert res.status_code == 200
        url = res.json['data']['relationships']['parent']['links']['related']['href']
        assert urlparse(url).path == url_public

    def test_node_has(self, app, url_public, project_public):

        #   test_node_has_children_link
        res = app.get(url_public)
        url = res.json['data']['relationships']['children']['links']['related']['href']
        expected_url = '{}children/'.format(url_public)
        assert urlparse(url).path == expected_url

    #   test_node_has_contributors_link
        url = res.json['data']['relationships']['contributors']['links']['related']['href']
        expected_url = '{}contributors/'.format(url_public)
        assert urlparse(url).path == expected_url

    #   test_node_has_node_links_link
        url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = '{}node_links/'.format(url_public)
        assert urlparse(url).path == expected_url

    #   test_node_has_registrations_link
        url = res.json['data']['relationships']['registrations']['links']['related']['href']
        expected_url = '{}registrations/'.format(url_public)
        assert urlparse(url).path == expected_url

    #   test_node_has_files_link
        url = res.json['data']['relationships']['files']['links']['related']['href']
        expected_url = '{}files/'.format(url_public)
        assert urlparse(url).path == expected_url

    #   test_node_has_affiliated_institutions_link_and_it_doesn't_serialize_to_none
        assert project_public.affiliated_institutions.count() == 0
        related_url = res.json['data']['relationships']['affiliated_institutions']['links']['related']['href']
        expected_url = '{}institutions/'.format(url_public)
        assert urlparse(related_url).path == expected_url
        self_url = res.json['data']['relationships']['affiliated_institutions']['links']['self']['href']
        expected_url = '{}relationships/institutions/'.format(url_public)
        assert urlparse(self_url).path == expected_url

    #   test_node_has_subjects_links_for_later_versions
        res = app.get(url_public + '?version={}'.format(subjects_as_relationships_version))
        related_url = res.json['data']['relationships']['subjects']['links']['related']['href']
        expected_url = '{}subjects/'.format(url_public)
        assert urlparse(related_url).path == expected_url
        self_url = res.json['data']['relationships']['subjects']['links']['self']['href']
        expected_url = '{}relationships/subjects/'.format(url_public)
        assert urlparse(self_url).path == expected_url

    def test_node_has_comments_link(
            self, app, user, project_public, url_public):
        CommentFactory(node=project_public, user=user)
        res = app.get(url_public)
        assert res.status_code == 200
        assert 'comments' in res.json['data']['relationships'].keys()
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data'][0]['type'] == 'comments'

    def test_node_comments_link_query_params_formatted(
            self, app, user, project_public, project_private, url_private):
        CommentFactory(node=project_public, user=user)
        project_private_link = PrivateLinkFactory(anonymous=False)
        project_private_link.nodes.add(project_private)
        project_private_link.save()

        res = app.get(url_private, auth=user.auth)
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        assert project_private_link.key not in url

        res = app.get(
            '{}?view_only={}'.format(
                url_private,
                project_private_link.key))
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        assert project_private_link.key in url

    def test_node_has_correct_unread_comments_count(
            self, app, user, project_public, url_public):
        contributor = AuthUserFactory()
        project_public.add_contributor(
            contributor=contributor, auth=Auth(user), save=True)
        CommentFactory(
            node=project_public,
            user=contributor,
            page='node')
        res = app.get(
            '{}?related_counts=True'.format(url_public),
            auth=user.auth)
        unread = res.json['data']['relationships']['comments']['links']['related']['meta']['unread']
        unread_comments_node = unread['node']
        assert unread_comments_node == 1

    def test_node_has_correct_wiki_page_count(self, user, app, url_private, project_private):
        res = app.get('{}?related_counts=True'.format(url_private), auth=user.auth)
        assert res.json['data']['relationships']['wikis']['links']['related']['meta']['count'] == 0

        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki_page = WikiFactory(node=project_private, user=user)
            WikiVersionFactory(wiki_page=wiki_page)

        res = app.get('{}?related_counts=True'.format(url_private), auth=user.auth)
        assert res.json['data']['relationships']['wikis']['links']['related']['meta']['count'] == 1

    def test_node_properties(self, app, url_public):
        res = app.get(url_public)
        assert res.json['data']['attributes']['public'] is True
        assert res.json['data']['attributes']['registration'] is False
        assert res.json['data']['attributes']['collection'] is False
        assert res.json['data']['attributes']['tags'] == []

    def test_requesting_folder_returns_error(self, app, user):
        folder = CollectionFactory(creator=user)
        res = app.get(
            '/{}nodes/{}/'.format(API_BASE, folder._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_cannot_return_registrations_at_node_detail_endpoint(
            self, app, user, project_public):
        registration = RegistrationFactory(
            project=project_public, creator=user)
        res = app.get('/{}nodes/{}/'.format(
            API_BASE, registration._id),
            auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_cannot_return_folder_at_node_detail_endpoint(self, app, user):
        folder = CollectionFactory(creator=user)
        res = app.get(
            '/{}nodes/{}/'.format(API_BASE, folder._id),
            auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_node_list_embed_identifier_link(self, app, user, project_public, url_public):
        url = url_public + '?embed=identifiers'
        res = app.get(url)
        assert res.status_code == 200
        link = res.json['data']['relationships']['identifiers']['links']['related']['href']
        assert '{}identifiers/'.format(url_public) in link

    def test_node_shows_wiki_relationship_based_on_disabled_status_and_version(self, app, user, project_public, url_public):
        url = url_public + '?version=latest'
        res = app.get(url, auth=user.auth)
        assert 'wikis' in res.json['data']['relationships']
        project_public.delete_addon('wiki', auth=Auth(user))
        project_public.save()
        res = app.get(url, auth=user.auth)
        assert 'wikis' not in res.json['data']['relationships']
        url = url_public + '?version=2.7'
        res = app.get(url, auth=user.auth)
        assert 'wikis' in res.json['data']['relationships']

    def test_preprint_field(self, app, user, user_two, project_public, url_public):
        # Returns true if project holds supplemental material for a preprint a user can view
        # Published preprint, admin_contrib
        preprint = PreprintFactory(project=project_public, creator=user)
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['preprint'] is True

        # Published preprint, non_contrib
        res = app.get(url_public, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['preprint'] is True

        # Unpublished preprint, admin contrib
        preprint.is_published = False
        preprint.save()
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['preprint'] is True

        # Unpublished preprint, non_contrib
        res = app.get(url_public, auth=user_two.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['preprint'] is False

    def test_shows_access_requests_enabled_field_based_on_version(self, app, user, project_public, url_public):
        url = url_public + '?version=latest'
        res = app.get(url, auth=user.auth)
        assert 'access_requests_enabled' not in res.json['data']['attributes']
        res = app.get(url_public + '?version=2.8', auth=user.auth)
        assert 'access_requests_enabled' in res.json['data']['attributes']

    def test_node_shows_correct_templated_from_count(self, app, user, project_public, url_public):
        url = url_public
        res = app.get(url)
        assert res.json['meta'].get('templated_by_count', False) is False
        url = url + '?related_counts=true'
        res = app.get(url)
        assert res.json['meta']['templated_by_count'] == 0
        ProjectFactory(title='template copy', template_node=project_public, creator=user)
        project_public.reload()
        res = app.get(url)
        assert res.json['meta']['templated_by_count'] == 1

    def test_node_show_correct_children_count(self, app, user, user_two, project_public, url_public):
        node_children_url = url_public + 'children/'
        url = url_public + '?related_counts=true'
        child = NodeFactory(parent=project_public, creator=user)
        res = app.get(url, auth=user.auth)
        # Child admin can view child
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 1
        res = app.get(node_children_url, auth=user.auth)
        assert len(res.json['data']) == 1

        # Implicit admin on parent can view child count
        res = app.get(url, auth=user_two.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0
        project_public.add_contributor(user_two, permissions.ADMIN)
        project_public.save()
        res = app.get(url, auth=user_two.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 1
        res = app.get(node_children_url, auth=user_two.auth)
        assert len(res.json['data']) == 1

        # Explicit Member of OSFGroup can view child count
        user_three = AuthUserFactory()
        group = OSFGroupFactory(creator=user_three)
        res = app.get(url, auth=user_three.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0
        child.add_osf_group(group, permissions.READ)
        res = app.get(url, auth=user_three.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 1
        res = app.get(node_children_url, auth=user_three.auth)
        assert len(res.json['data']) == 1

        # Implicit admin group member can view child count
        child.remove_osf_group(group)
        res = app.get(url, auth=user_three.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0

        project_public.add_osf_group(group, permissions.ADMIN)
        res = app.get(url, auth=user_three.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 1
        res = app.get(node_children_url, auth=user_three.auth)
        assert len(res.json['data']) == 1

        # Grandchildren not shown. Children show one level.
        grandparent = AuthUserFactory()
        NodeFactory(parent=child, creator=user)
        project_public.add_contributor(grandparent, permissions.ADMIN)
        project_public.save()
        res = app.get(node_children_url, auth=grandparent.auth)
        assert len(res.json['data']) == 1
        res = app.get(url, auth=grandparent.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 1

        NodeFactory(parent=project_public, creator=user)
        res = app.get(node_children_url, auth=grandparent.auth)
        assert len(res.json['data']) == 2
        res = app.get(url, auth=grandparent.auth)
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 2

    def test_node_shows_related_count_for_linked_by_relationships(self, app, user, project_public, url_public, project_private):
        url = url_public + '?related_counts=true'
        res = app.get(url)
        assert 'count' in res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']
        assert 'count' in res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']
        assert res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']['count'] == 0

        project_private.add_pointer(project_public, auth=Auth(user), save=True)
        project_public.reload()

        res = app.get(url)
        assert 'count' in res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']
        assert 'count' in res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']
        assert res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']['count'] == 1
        assert res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']['count'] == 0

        registration = RegistrationFactory(project=project_private, creator=user)
        project_public.reload()

        res = app.get(url)
        assert 'count' in res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']
        assert 'count' in res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']
        assert res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']['count'] == 1
        assert res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']['count'] == 1

        project_private.is_deleted = True
        project_private.save()
        project_public.reload()

        res = app.get(url)
        assert 'count' in res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']
        assert 'count' in res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']
        assert res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']['count'] == 1

        WithdrawnRegistrationFactory(registration=registration, user=user)
        project_public.reload()

        res = app.get(url)
        assert 'count' in res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']
        assert 'count' in res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']
        assert res.json['data']['relationships']['linked_by_nodes']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['linked_by_registrations']['links']['related']['meta']['count'] == 0

    def test_node_shows_correct_forks_count_including_private_forks(self, app, user, project_private, url_private, user_two):
        project_private.add_contributor(
            user_two,
            permissions=permissions.ADMIN,
            auth=Auth(user)
        )
        url = url_private + '?related_counts=true'
        forks_url = url_private + 'forks/'
        res = app.get(url, auth=user.auth)
        assert 'count' in res.json['data']['relationships']['forks']['links']['related']['meta']
        assert res.json['data']['relationships']['forks']['links']['related']['meta']['count'] == 0
        res = app.get(forks_url, auth=user.auth)
        assert len(res.json['data']) == 0

        ForkFactory(project=project_private, user=user_two)
        project_private.reload()

        res = app.get(url, auth=user.auth)
        assert 'count' in res.json['data']['relationships']['forks']['links']['related']['meta']
        assert res.json['data']['relationships']['forks']['links']['related']['meta']['count'] == 1
        res = app.get(forks_url, auth=user.auth)
        assert len(res.json['data']) == 0

        ForkFactory(project=project_private, user=user)
        project_private.reload()

        res = app.get(url, auth=user.auth)
        assert 'count' in res.json['data']['relationships']['forks']['links']['related']['meta']
        assert res.json['data']['relationships']['forks']['links']['related']['meta']['count'] == 2
        res = app.get(forks_url, auth=user.auth)
        assert len(res.json['data']) == 1

    def test_current_user_permissions(self, app, user, url_public, project_public, user_two):
        # in most recent API version, read isn't implicit for public nodes
        url = url_public + '?version=2.11'
        res = app.get(url, auth=user_two.auth)
        assert not project_public.has_permission(user_two, permissions.READ)
        assert permissions.READ not in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # ensure read is not included for an anonymous user
        res = app.get(url)
        assert permissions.READ not in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # ensure both read and write included for a write contributor
        new_user = AuthUserFactory()
        project_public.add_contributor(
            new_user,
            permissions=permissions.WRITE,
            auth=Auth(project_public.creator)
        )
        res = app.get(url, auth=new_user.auth)
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.WRITE, permissions.READ]
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is True

        # make sure 'read' is there for implicit read contributors
        comp = NodeFactory(parent=project_public, is_public=True)
        comp_url = '/{}nodes/{}/?version=2.11'.format(API_BASE, comp._id)
        res = app.get(comp_url, auth=user.auth)
        assert project_public.has_permission(user, permissions.ADMIN)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # ensure 'read' is still included with older versions
        res = app.get(url_public, auth=user_two.auth)
        assert not project_public.has_permission(user_two, permissions.READ)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # check read permission is included with older versions for anon user
        res = app.get(url_public)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # Read group member has "read" permissions
        group_member = AuthUserFactory()
        osf_group = OSFGroupFactory(creator=group_member)
        project_public.add_osf_group(osf_group, permissions.READ)
        res = app.get(url, auth=group_member.auth)
        assert project_public.has_permission(group_member, permissions.READ)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is True

        # Write group member has "read" and "write" permissions
        group_member = AuthUserFactory()
        osf_group = OSFGroupFactory(creator=group_member)
        project_public.add_osf_group(osf_group, permissions.WRITE)
        res = app.get(url, auth=group_member.auth)
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.WRITE, permissions.READ]
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is True

        # Admin group member has "read" and "write" and "admin" permissions
        group_member = AuthUserFactory()
        osf_group = OSFGroupFactory(creator=group_member)
        project_public.add_osf_group(osf_group, permissions.ADMIN)
        res = app.get(url, auth=group_member.auth)
        assert res.json['data']['attributes']['current_user_permissions'] == [permissions.ADMIN, permissions.WRITE, permissions.READ]
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is True

        # make sure 'read' is there for implicit read group members
        comp = NodeFactory(parent=project_public, is_public=True)
        comp_url = '/{}nodes/{}/?version=2.11'.format(API_BASE, comp._id)
        res = app.get(comp_url, auth=group_member.auth)
        assert project_public.has_permission(user, permissions.ADMIN)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # ensure 'read' is still included with older versions
        project_public.remove_osf_group(osf_group)
        res = app.get(url_public, auth=group_member.auth)
        assert not project_public.has_permission(group_member, permissions.READ)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False

        # superusers current permissions are None
        superuser = AuthUserFactory()
        superuser.is_superuser = True
        superuser.save()

        res = app.get(url, auth=superuser.auth)
        assert not project_public.has_permission(superuser, permissions.READ)
        assert permissions.READ not in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False
        assert res.json['data']['attributes']['current_user_is_contributor'] is False

        res = app.get(url_public, auth=superuser.auth)
        assert not project_public.has_permission(superuser, permissions.READ)
        assert permissions.READ in res.json['data']['attributes']['current_user_permissions']
        assert res.json['data']['attributes']['current_user_is_contributor_or_group_member'] is False
        assert res.json['data']['attributes']['current_user_is_contributor'] is False


@pytest.mark.django_db
class NodeCRUDTestCase:

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_two(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_two(self, institution_one, institution_two):
        auth_user = AuthUserFactory()
        auth_user.affiliated_institutions.add(institution_one)
        auth_user.affiliated_institutions.add(institution_two)
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
        # Sets public project storage cache to avoid need for retries in tests
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project._id)
        storage_usage_cache.set(key, 0, settings.STORAGE_USAGE_CACHE_TIMEOUT)
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
        return '/{}nodes/{}/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/'.format(API_BASE, project_private._id)

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
class TestNodeUpdate(NodeCRUDTestCase):

    def test_node_institution_update(self, app, user_two, project_private, url_private, make_node_payload,
                                     institution_one, institution_two):
        project_private.add_contributor(
            user_two,
            permissions=permissions.ADMIN,
            auth=Auth(project_private.creator)
        )
        affiliated_institutions = {
            'affiliated_institutions':
                {'data': [
                    {
                        'type': 'institutions',
                        'id': institution_one._id
                    },
                    {
                        'type': 'institutions',
                        'id': institution_two._id
                    },
                ]
                }
        }
        payload = make_node_payload(project_private, {'public': False}, relationships=affiliated_institutions)
        res = app.patch_json_api(url_private, payload, auth=user_two.auth, expect_errors=False)
        assert res.status_code == 200
        institutions = project_private.affiliated_institutions.all()
        assert institution_one in institutions
        assert institution_two in institutions

    def test_node_update_invalid_data(self, app, user, url_public):
        res = app.put_json_api(
            url_public, 'Incorrect data',
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

        res = app.put_json_api(
            url_public, ['Incorrect data'],
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_cannot_make_project_public_if_non_contributor(
            self, app, project_private, url_private, make_node_payload):
        with assert_latest_log_not(NodeLog.MADE_PUBLIC, project_private):
            non_contrib = AuthUserFactory()
            res = app.patch_json(
                url_private,
                make_node_payload(project_private, {'public': True}),
                auth=non_contrib.auth, expect_errors=True
            )
            assert res.status_code == 403

    def test_cannot_make_project_public_if_non_admin_contributor(
            self, app, project_private, url_private, make_node_payload):
        non_admin = AuthUserFactory()
        project_private.add_contributor(
            non_admin,
            permissions=permissions.WRITE,
            auth=Auth(project_private.creator)
        )
        project_private.save()
        res = app.patch_json(
            url_private,
            make_node_payload(project_private, {'public': True}),
            auth=non_admin.auth, expect_errors=True
        )
        assert res.status_code == 403

        project_private.reload()
        assert not project_private.is_public

    def test_can_make_project_public_if_admin_contributor(
            self, app, project_private, url_private, make_node_payload):
        with assert_latest_log(NodeLog.MADE_PUBLIC, project_private):
            admin_user = AuthUserFactory()
            project_private.add_contributor(
                admin_user,
                permissions=permissions.ADMIN,
                auth=Auth(project_private.creator))
            project_private.save()
            res = app.patch_json_api(
                url_private,
                make_node_payload(project_private, {'public': True}),
                auth=admin_user.auth  # self.user is creator/admin
            )
            assert res.status_code == 200
            project_private.reload()
            assert project_private.is_public

    def test_make_project_private_uncalculated_storage_limit(
        self, app, url_public, project_public, user
    ):
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.delete(key)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This project\'s node storage usage could not be calculated. Please try again.'

    def test_make_project_private_over_storage_limit(
        self, app, url_public, project_public, user
    ):
        # If the public node exceeds the the private storage limit
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE + 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This project exceeds private project storage limits and thus cannot be converted into a private project.'

    def test_make_project_private_under_storage_limit(
        self, app, url_public, project_public, user
    ):
        # If the public node does not exceed the private storage limit
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_public._id)
        storage_usage_cache.set(key, (settings.STORAGE_LIMIT_PRIVATE - 1) * settings.GBs, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'public': False
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is False

    def test_update_errors(
            self, app, user, user_two, title_new, description_new,
            category_new, project_public, project_private,
            url_public, url_private):

        #   test_update_project_properties_not_nested
        res = app.put_json_api(url_public, {
            'id': project_public._id,
            'type': 'nodes',
            'title': title_new,
            'description': description_new,
            'category': category_new,
            'public': True,
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'
        assert res.json['errors'][0]['source']['pointer'] == '/data'

        #   test_update_invalid_id
        res = app.put_json_api(url_public, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_invalid_type
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'node',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_update_no_id
        res = app.put_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_update_no_type
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_update_public_project_logged_out
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_update_project_invalid_title
        project = {
            'data': {
                'type': 'nodes',
                'id': project_public._id,
                'attributes': {
                    'title': 'A' * 513,
                    'category': 'project',
                }
            }
        }
        res = app.put_json_api(
            url_public, project,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Title cannot exceed 512 characters.'

    #   test_update_public_project_logged_in_but_unauthorized
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_update_private_project_logged_out
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_update_private_project_logged_in_non_contributor
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    # test_update_private_project_group_has_read_perms
        osf_group = OSFGroupFactory(creator=user_two)
        project_private.add_osf_group(osf_group, permissions.READ)
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert project_private.has_permission(user_two, permissions.READ) is True
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_update_public_project_logged_in(
            self, app, user, title_new, description_new,
            category_new, project_public, url_public):
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': True
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == title_new
        assert res.json['data']['attributes']['description'] == description_new
        assert res.json['data']['attributes']['category'] == category_new
        log_actions = project_public.logs.values_list('action', flat=True)
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_update_public_project_osf_group_member(
        self, app, user_two, title_new, description_new,
            category_new, project_public, url_public):
        osf_group = OSFGroupFactory(creator=user_two)
        project_public.add_osf_group(osf_group, permissions.WRITE)
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                }
            }
        }, auth=user_two.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == title_new
        assert res.json['data']['attributes']['description'] == description_new
        assert res.json['data']['attributes']['category'] == category_new
        log_actions = project_public.logs.values_list('action', flat=True)
        assert NodeLog.CATEGORY_UPDATED in log_actions
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions

    def test_cannot_update_a_registration(self, app, user, project_public):
        registration = RegistrationFactory(
            project=project_public, creator=user)
        original_title = registration.title
        original_description = registration.description
        url = '/{}nodes/{}/'.format(API_BASE, registration._id)
        res = app.put_json_api(url, {
            'data': {
                'id': registration._id,
                'type': 'nodes',
                'attributes': {
                    'title': fake.catch_phrase(),
                    'description': fake.bs(),
                    'category': 'hypothesis',
                    'public': True
                }
            }
        }, auth=user.auth, expect_errors=True)
        registration.reload()
        assert res.status_code == 404
        assert registration.title == original_title
        assert registration.description == original_description

    def test_update_private_project_logged_in_contributor(
            self, app, user, title_new, description_new,
            category_new, project_private, url_private):
        res = app.put_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                    'description': description_new,
                    'category': category_new,
                    'public': False
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == title_new
        assert res.json['data']['attributes']['description'] == description_new
        assert res.json['data']['attributes']['category'] == category_new
        log_actions = [log.action for log in project_private.logs.all()]
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_update_project_sanitizes_html_properly(
            self, app, user, category_new, project_public, url_public):
        """Post request should update resource, and any HTML in fields should be stripped"""
        new_title = '<strong>Super</strong> Cool Project'
        new_description = 'An <script>alert("even cooler")</script> project'
        res = app.put_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': new_title,
                    'description': new_description,
                    'category': category_new,
                    'public': True,
                }
            }
        }, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert res.json['data']['attributes']['title'] == strip_html(
            new_title)
        assert res.json['data']['attributes']['description'] == strip_html(
            new_description)
        log_actions = [log.action for log in project_public.logs.all()]
        assert NodeLog.EDITED_TITLE in log_actions
        assert NodeLog.EDITED_DESCRIPTION in log_actions
        assert NodeLog.CATEGORY_UPDATED in log_actions

    def test_partial_update_project_updates_project_correctly_and_sanitizes_html(
            self, app, user, description, category, project_public, url_public):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_public):
            new_title = 'An <script>alert("even cooler")</script> project'
            res = app.patch_json_api(url_public, {
                'data': {
                    'id': project_public._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': new_title
                    }
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'

            res = app.get(url_public)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == strip_html(
                new_title)
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_partial_update_public_project_logged_in(
            self, app, user, title_new, description,
            category, project_public, url_public):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_public):
            res = app.patch_json_api(url_public, {
                'data': {
                    'id': project_public._id,
                    'type': 'nodes',
                    'attributes': {
                        'title': title_new,
                    }
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_write_to_public_field_non_contrib_forbidden(
            self, app, user_two, project_public, url_public):
        # Test non-contrib writing to public field
        res = app.patch_json_api(url_public, {
            'data': {
                'attributes': {
                    'public': False},
                'id': project_public._id,
                'type': 'nodes'
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    def test_partial_update_errors(
            self, app, user, user_two, title_new,
            project_public, project_private,
            url_public, url_private):

        #   test_partial_update_public_project_logged_out
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_public_project_logged_in_but_unauthorized
        # Public resource, logged in, unauthorized
        res = app.patch_json_api(url_public, {
            'data': {
                'attributes': {
                    'title': title_new},
                'id': project_public._id,
                'type': 'nodes',
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_private_project_logged_out
        res = app.patch_json_api(url_private, {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'title': title_new
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_private_project_logged_in_non_contributor
        res = app.patch_json_api(url_private, {
            'data': {
                'attributes': {
                    'title': title_new},
                'id': project_private._id,
                'type': 'nodes',
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_partial_update_invalid_id
        res = app.patch_json_api(url_public, {
            'data': {
                'id': '12345',
                'type': 'nodes',
                'attributes': {
                        'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_invalid_type
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'node',
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 409

    #   test_partial_update_no_id
        res = app.patch_json_api(url_public, {
            'data': {
                'type': 'nodes',
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/id'

    #   test_partial_update_no_type
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'attributes': {
                    'title': title_new,
                }
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   Nothing will be updated here
    #   test_partial_update_project_properties_not_nested
        res = app.patch_json_api(url_public, {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'title': title_new,
            }
        }, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

    def test_partial_update_private_project_logged_in_contributor(
            self, app, user, title_new, description, category, project_private, url_private):
        with assert_latest_log(NodeLog.EDITED_TITLE, project_private):
            res = app.patch_json_api(url_private, {
                'data': {
                    'attributes': {
                        'title': title_new},
                    'id': project_private._id,
                    'type': 'nodes',
                }
            }, auth=user.auth)
            assert res.status_code == 200
            assert res.content_type == 'application/vnd.api+json'
            assert res.json['data']['attributes']['title'] == title_new
            assert res.json['data']['attributes']['description'] == description
            assert res.json['data']['attributes']['category'] == category

    def test_multiple_patch_requests_with_same_category_generates_one_log(
            self, app, user, project_private, url_private, make_node_payload):
        project_private.category = 'project'
        project_private.save()
        new_category = 'data'
        payload = make_node_payload(
            project_private,
            attributes={'category': new_category})
        original_n_logs = project_private.logs.count()

        res = app.patch_json_api(url_private, payload, auth=user.auth)
        assert res.status_code == 200
        project_private.reload()
        assert project_private.category == new_category
        assert project_private.logs.count() == original_n_logs + 1  # sanity check

        app.patch_json_api(url_private, payload, auth=user.auth)
        project_private.reload()
        assert project_private.category == new_category
        assert project_private.logs.count() == original_n_logs + 1

    def test_public_project_with_publicly_editable_wiki_turns_private(
            self, app, user, project_public, url_public, make_node_payload):
        wiki = project_public.get_addon('wiki')
        wiki.set_editing(permissions=True, auth=Auth(user=user), log=True)
        res = app.patch_json_api(
            url_public,
            make_node_payload(project_public, {'public': False}),
            auth=user.auth  # self.user is creator/admin
        )
        assert res.status_code == 200

    @mock.patch('website.identifiers.tasks.update_doi_metadata_on_change.s')
    def test_set_node_private_updates_doi(
            self, mock_update_doi_metadata, app, user, project_public,
            url_public, make_node_payload):

        IdentifierFactory(referent=project_public, category='doi')
        res = app.patch_json_api(
            url_public,
            make_node_payload(
                project_public,
                {'public': False}),
            auth=user.auth)
        assert res.status_code == 200
        project_public.reload()
        assert not project_public.is_public
        mock_update_doi_metadata.assert_called_with(project_public._id)

    @pytest.mark.enable_enqueue_task
    @mock.patch('website.preprints.tasks.update_or_enqueue_on_preprint_updated')
    def test_set_node_with_preprint_private_updates_doi(
            self, mock_update_doi_metadata, app, user,
            project_public, url_public, make_node_payload):
        target_object = PreprintFactory(project=project_public)

        res = app.patch_json_api(
            url_public,
            make_node_payload(
                project_public,
                {'public': False}),
            auth=user.auth)
        assert res.status_code == 200
        project_public.reload()
        assert not project_public.is_public
        # Turning supplemental_project private no longer turns preprint private
        assert target_object.is_public
        assert not mock_update_doi_metadata.called


@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
class TestNodeDelete(NodeCRUDTestCase):

    def test_deletes_node_errors(
            self, app, user, user_two, project_public,
            project_private, url_public, url_private,
            url_fake):

        #   test_deletes_public_node_logged_out
        res = app.delete(url_public, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_deletes_public_node_fails_if_unauthorized
        res = app.delete_json_api(
            url_public,
            auth=user_two.auth,
            expect_errors=True)
        project_public.reload()
        assert res.status_code == 403
        assert project_public.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    #   test_deletes_private_node_logged_out
        res = app.delete(url_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_deletes_private_node_logged_in_non_contributor
        res = app.delete(url_private, auth=user_two.auth, expect_errors=True)
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    #   test_deletes_invalid_node
        res = app.delete(url_fake, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert 'detail' in res.json['errors'][0]

    #   test_delete_osf_group_improper_permissions
        osf_group = OSFGroupFactory(creator=user_two)
        project_private.add_osf_group(osf_group, permissions.READ)
        res = app.delete(url_private, auth=user_two.auth, expect_errors=True)
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_read_only_contributor(
            self, app, user_two, project_private, url_private):
        project_private.add_contributor(
            user_two, permissions=permissions.READ)
        project_private.save()
        res = app.delete(url_private, auth=user_two.auth, expect_errors=True)
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_write_contributor(
            self, app, user_two, project_private, url_private):
        project_private.add_contributor(
            user_two, permissions=permissions.WRITE)
        project_private.save()
        res = app.delete(url_private, auth=user_two.auth, expect_errors=True)
        project_private.reload()
        assert res.status_code == 403
        assert project_private.is_deleted is False
        assert 'detail' in res.json['errors'][0]

    def test_delete_project_with_component_returns_errors_pre_2_12(self, app, user):
        project = ProjectFactory(creator=user)
        NodeFactory(parent=project, creator=user)
        # Return a 400 because component must be deleted before deleting the
        # parent
        res = app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, project._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        errors = res.json['errors']
        assert len(errors) == 1
        assert (
            errors[0]['detail'] ==
            'Any child components must be deleted prior to deleting this project.')

    def test_delete_project_with_component_allowed_with_2_12(self, app, user):
        project = ProjectFactory(creator=user)
        child = NodeFactory(parent=project, creator=user)
        grandchild = NodeFactory(parent=child, creator=user)
        # Versions 2.12 and greater delete all the nodes in the hierarchy
        res = app.delete_json_api(
            '/{}nodes/{}/?version=2.12'.format(API_BASE, project._id),
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 204
        project.reload()
        child.reload()
        grandchild.reload()
        assert project.is_deleted is True
        assert child.is_deleted is True
        assert grandchild.is_deleted is True

    def test_delete_project_with_private_component_2_12(self, app, user):
        user_two = AuthUserFactory()
        project = ProjectFactory(creator=user)
        child = NodeFactory(parent=project, creator=user_two)
        # Versions 2.12 and greater delete all the nodes in the hierarchy
        res = app.delete_json_api(
            '/{}nodes/{}/?version=2.12'.format(API_BASE, project._id),
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        project.reload()
        child.reload()
        assert project.is_deleted is False
        assert child.is_deleted is False

    def test_delete_bookmark_collection_returns_error(self, app, user):
        bookmark_collection = find_bookmark_collection(user)
        res = app.delete_json_api(
            '/{}nodes/{}/'.format(API_BASE, bookmark_collection._id),
            auth=user.auth,
            expect_errors=True
        )
        # Bookmark collections are collections, so a 404 is returned
        assert res.status_code == 404

    @mock.patch('website.identifiers.tasks.update_doi_metadata_on_change.s')
    def test_delete_node_with_preprint_calls_preprint_update_status(
            self, mock_update_doi_metadata_on_change, app, user,
            project_public, url_public):
        PreprintFactory(project=project_public)
        app.delete_json_api(url_public, auth=user.auth, expect_errors=True)
        project_public.reload()

        assert not mock_update_doi_metadata_on_change.called

    @mock.patch('website.identifiers.tasks.update_doi_metadata_on_change.s')
    def test_delete_node_with_identifier_calls_preprint_update_status(
            self, mock_update_doi_metadata_on_change, app, user,
            project_public, url_public):
        IdentifierFactory(referent=project_public, category='doi')
        app.delete_json_api(url_public, auth=user.auth, expect_errors=True)
        project_public.reload()

        assert mock_update_doi_metadata_on_change.called

    def test_deletes_public_node_succeeds_as_owner(
            self, app, user, project_public, url_public):
        with assert_latest_log(NodeLog.PROJECT_DELETED, project_public):
            res = app.delete_json_api(
                url_public, auth=user.auth, expect_errors=True)
            project_public.reload()
            assert res.status_code == 204
            assert project_public.is_deleted is True

    def test_requesting_deleted_returns_410(
            self, app, project_public, url_public):
        project_public.is_deleted = True
        project_public.save()
        res = app.get(url_public, expect_errors=True)
        assert res.status_code == 410
        assert 'detail' in res.json['errors'][0]

    def test_deletes_private_node_logged_in_contributor(
            self, app, user, project_private, url_private):
        with assert_latest_log(NodeLog.PROJECT_DELETED, project_private):
            res = app.delete(url_private, auth=user.auth, expect_errors=True)
            project_private.reload()
            assert res.status_code == 204
            assert project_private.is_deleted is True


@pytest.mark.django_db
class TestReturnDeletedNode:

    @pytest.fixture()
    def project_public_deleted(self, user):
        return ProjectFactory(
            is_deleted=True,
            creator=user,
            title='This public project has been deleted',
            category='project',
            is_public=True
        )

    @pytest.fixture()
    def project_private_deleted(self, user):
        return ProjectFactory(
            is_deleted=True,
            creator=user,
            title='This private project has been deleted',
            category='project',
            is_public=False
        )

    @pytest.fixture()
    def title_new(self):
        return 'This deleted node has been edited'

    @pytest.fixture()
    def url_project_public_deleted(self, project_public_deleted):
        return '/{}nodes/{}/'.format(API_BASE, project_public_deleted._id)

    @pytest.fixture()
    def url_project_private_deleted(self, project_private_deleted):
        return '/{}nodes/{}/'.format(API_BASE, project_private_deleted._id)

    def test_return_deleted_node(
            self, app, user, title_new, project_public_deleted,
            project_private_deleted, url_project_public_deleted,
            url_project_private_deleted):

        #   test_return_deleted_public_node
        res = app.get(url_project_public_deleted, expect_errors=True)
        assert res.status_code == 410

    #   test_return_deleted_private_node
        res = app.get(
            url_project_private_deleted,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410

    #   test_edit_deleted_public_node
        res = app.put_json_api(
            url_project_public_deleted,
            params={
                'title': title_new,
                'node_id': project_public_deleted._id,
                'category': project_public_deleted.category
            },
            auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    #   test_edit_deleted_private_node
        res = app.put_json_api(
            url_project_private_deleted,
            params={
                'title': title_new,
                'node_id': project_private_deleted._id,
                'category': project_private_deleted.category
            },
            auth=user.auth, expect_errors=True)
        assert res.status_code == 410

    #   test_delete_deleted_public_node
        res = app.delete(
            url_project_public_deleted,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410

    #   test_delete_deleted_private_node
        res = app.delete(
            url_project_private_deleted,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 410


@pytest.mark.django_db
class TestUpdateNodeSubjects(UpdateSubjectsMixin):

    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        project = ProjectFactory(is_public=True, creator=user_admin_contrib)
        project.add_contributor(user_write_contrib, permissions=permissions.WRITE)
        project.add_contributor(user_read_contrib, permissions=permissions.READ)
        project.save()
        return project


@pytest.mark.django_db
class TestNodeTags:

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user, user_admin):
        project_public = ProjectFactory(
            title='Project One', is_public=True, creator=user)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        return project_public

    @pytest.fixture()
    def project_private(self, user, user_admin):
        project_private = ProjectFactory(
            title='Project Two', is_public=False, creator=user)
        project_private.add_contributor(
            user_admin, permissions=permissions.CREATOR_PERMISSIONS, save=True)
        project_private.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        # Sets private project storage cache to avoid need for retries in tests updating public status
        key = cache_settings.STORAGE_USAGE_KEY.format(target_id=project_private._id)
        storage_usage_cache.set(key, 0, settings.STORAGE_USAGE_CACHE_TIMEOUT)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/'.format(API_BASE, project_private._id)

    @pytest.fixture()
    def payload_public(self, project_public):
        return {
            'data': {
                'id': project_public._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    @pytest.fixture()
    def payload_private(self, project_private):
        return {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'tags': ['new-tag']
                }
            }
        }

    def test_public_project_starts_with_no_tags(self, app, url_public):
        res = app.get(url_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    def test_node_detail_does_not_expose_system_tags(
            self, app, project_public, url_public):
        project_public.add_system_tag('systag', save=True)
        res = app.get(url_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

    def test_contributor_can_add_tag_to_public_project(
            self, app, user, project_public, payload_public, url_public):
        with assert_latest_log(NodeLog.TAG_ADDED, project_public):
            res = app.patch_json_api(
                url_public,
                payload_public,
                auth=user.auth,
                expect_errors=True)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            project_public.reload()
            assert project_public.tags.count() == 1
            assert project_public.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_public)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

    def test_contributor_can_add_tag_to_private_project(
            self, app, user, project_private, payload_private, url_private):
        with assert_latest_log(NodeLog.TAG_ADDED, project_private):
            res = app.patch_json_api(
                url_private, payload_private, auth=user.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            project_private.reload()
            assert project_private.tags.count() == 1
            assert project_private.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_private, auth=user.auth)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

    def test_partial_update_project_does_not_clear_tags(
            self, app, user_admin, project_private, payload_private, url_private):
        res = app.patch_json_api(
            url_private,
            payload_private,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1
        new_payload = {
            'data': {
                'id': project_private._id,
                'type': 'nodes',
                'attributes': {
                    'public': True
                }
            }
        }
        res = app.patch_json_api(
            url_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1
        new_payload['data']['attributes']['public'] = False
        res = app.patch_json_api(
            url_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1

    def test_add_tag_to_project_errors(
            self, app, user_non_contrib, user_read_contrib,
            payload_public, payload_private,
            url_public, url_private):

        #   test_non_authenticated_user_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True, auth=None)
        assert res.status_code == 401

    #   test_non_authenticated_user_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True, auth=None)
        assert res.status_code == 401

    #   test_non_contributor_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True, auth=user_non_contrib.auth)
        assert res.status_code == 403

    #   test_non_contributor_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True, auth=user_non_contrib.auth)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_add_tag_to_public_project
        res = app.patch_json_api(
            url_public, payload_public,
            expect_errors=True,
            auth=user_read_contrib.auth)
        assert res.status_code == 403

    #   test_read_only_contributor_cannot_add_tag_to_private_project
        res = app.patch_json_api(
            url_private, payload_private,
            expect_errors=True,
            auth=user_read_contrib.auth)
        assert res.status_code == 403

    def test_tags_add_and_remove_properly(
            self, app, user, project_private,
            payload_private, url_private):
        with assert_latest_log(NodeLog.TAG_ADDED, project_private):
            res = app.patch_json_api(
                url_private, payload_private, auth=user.auth)
            assert res.status_code == 200
            # Ensure adding tag data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, project_private), assert_latest_log(NodeLog.TAG_ADDED, project_private, 1):
            # Ensure removing and adding tag data is correct from the PATCH
            # response
            res = app.patch_json_api(
                url_private,
                {
                    'data': {
                        'id': project_private._id,
                        'type': 'nodes',
                        'attributes': {'tags': ['newer-tag']}
                    }
                }, auth=user.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'newer-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, project_private):
            # Ensure removing tag data is correct from the PATCH response
            res = app.patch_json_api(
                url_private,
                {
                    'data': {
                        'id': project_private._id,
                        'type': 'nodes',
                        'attributes': {'tags': []}
                    }
                }, auth=user.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 0

    def test_tags_post_object_instead_of_list(self, user, app):
        url = '/{}nodes/'.format(API_BASE)
        payload = {'data': {
            'type': 'nodes',
            'attributes': {
                'title': 'new title',
                'category': 'project',
                'tags': {'foo': 'bar'}
            }
        }}
        res = app.post_json_api(
            url, payload, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    def test_tags_patch_object_instead_of_list(
            self, app, user, payload_public, url_public):
        payload_public['data']['attributes']['tags'] = {'foo': 'bar'}
        res = app.patch_json_api(
            url_public, payload_public,
            auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'


@pytest.mark.django_db
class TestNodeLicense:

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def license_name(self):
        return 'MIT License'

    @pytest.fixture()
    def node_license(self, license_name):
        return NodeLicense.objects.filter(name=license_name).first()

    @pytest.fixture()
    def year(self):
        return '2105'

    @pytest.fixture()
    def copyright_holders(self):
        return ['Foo', 'Bar']

    @pytest.fixture()
    def project_public(
            self, user, user_admin, node_license,
            year, copyright_holders):
        project_public = ProjectFactory(
            title='Project One', is_public=True, creator=user)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        project_public.node_license = NodeLicenseRecordFactory(
            node_license=node_license,
            year=year,
            copyright_holders=copyright_holders
        )
        project_public.save()
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_admin, node_license,
            year, copyright_holders):
        project_private = ProjectFactory(
            title='Project Two', is_public=False, creator=user)
        project_private.add_contributor(
            user_admin, permissions=permissions.CREATOR_PERMISSIONS, save=True)
        project_private.add_contributor(
            user, permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS, save=True)
        project_private.node_license = NodeLicenseRecordFactory(
            node_license=node_license,
            year=year,
            copyright_holders=copyright_holders
        )
        project_private.save()
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}nodes/{}/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}nodes/{}/'.format(API_BASE, project_private._id)

    def test_node_has(
            self, app, user, node_license, project_public,
            project_private, url_private, url_public):

        #   test_public_node_has_node_license
        res = app.get(url_public)
        assert project_public.node_license.year == res.json[
            'data']['attributes']['node_license']['year']

    #   test_public_node_has_license_relationship
        res = app.get(url_public)
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert expected_license_url in actual_license_url

    #   test_private_node_has_node_license
        res = app.get(url_private, auth=user.auth)
        assert project_private.node_license.year == res.json[
            'data']['attributes']['node_license']['year']

    #   test_private_node_has_license_relationship
        res = app.get(url_private, auth=user.auth)
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        assert expected_license_url in actual_license_url

    def test_component_return_parent_license_if_no_license(
            self, app, user, node_license, project_public):
        node = NodeFactory(parent=project_public, creator=user)
        node.save()
        node_url = '/{}nodes/{}/'.format(API_BASE, node._id)
        res = app.get(node_url, auth=user.auth)
        assert not node.node_license
        assert project_public.node_license.year == \
               res.json['data']['attributes']['node_license']['year']
        actual_license_url = res.json['data']['relationships']['license']['links']['related']['href']
        expected_license_url = '/{}licenses/{}'.format(
            API_BASE, node_license._id)
        assert expected_license_url in actual_license_url


@pytest.mark.django_db
class TestNodeUpdateLicense:

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
    def node(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        node = NodeFactory(creator=user_admin_contrib)
        node.add_contributor(user_write_contrib, auth=Auth(user_admin_contrib))
        node.add_contributor(
            user_read_contrib,
            auth=Auth(user_admin_contrib),
            permissions=permissions.READ)
        node.save()
        return node

    @pytest.fixture()
    def license_cc0(self):
        return NodeLicense.objects.filter(name='CC0 1.0 Universal').first()

    @pytest.fixture()
    def license_mit(self):
        return NodeLicense.objects.filter(name='MIT License').first()

    @pytest.fixture()
    def license_no(self):
        return NodeLicense.objects.get(name='No license')

    @pytest.fixture()
    def url_node(self, node):
        return '/{}nodes/{}/'.format(API_BASE, node._id)

    @pytest.fixture()
    def make_payload(self):
        def payload(
                node_id, license_id=None, license_year=None,
                copyright_holders=None):
            attributes = {}

            if license_year and copyright_holders:
                attributes = {
                    'node_license': {
                        'year': license_year,
                        'copyright_holders': copyright_holders
                    }
                }
            elif license_year:
                attributes = {
                    'node_license': {
                        'year': license_year
                    }
                }
            elif copyright_holders:
                attributes = {
                    'node_license': {
                        'copyright_holders': copyright_holders
                    }
                }

            return {
                'data': {
                    'type': 'nodes',
                    'id': node_id,
                    'attributes': attributes,
                    'relationships': {
                        'license': {
                            'data': {
                                'type': 'licenses',
                                'id': license_id
                            }
                        }
                    }
                }
            } if license_id else {
                'data': {
                    'type': 'nodes',
                    'id': node_id,
                    'attributes': attributes
                }
            }
        return payload

    @pytest.fixture()
    def make_request(self, app):
        def request(url, data, auth=None, expect_errors=False):
            return app.patch_json_api(
                url, data, auth=auth, expect_errors=expect_errors)
        return request

    def test_admin_update_license_with_invalid_id(
            self, user_admin_contrib, node, make_payload,
            make_request, url_node):
        data = make_payload(
            node_id=node._id,
            license_id='thisisafakelicenseid'
        )

        assert node.node_license is None

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == 'Unable to find specified license.'

        node.reload()
        assert node.node_license is None

    def test_admin_can_update_license(
            self, user_admin_contrib, node,
            make_payload, make_request,
            license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        assert node.node_license is None

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year is None
        assert node.node_license.copyright_holders == []

    def test_admin_can_update_license_record(
            self, user_admin_contrib, node,
            make_payload, make_request,
            license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='2015',
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        assert node.node_license is None

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update(
            self, user_write_contrib, user_read_contrib,
            user_non_contrib, node, make_payload,
            make_request, license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['id'] == node._id

    # def test_read_contributor_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_read_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_non_contributor_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(
            url_node, data,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_unauthenticated_user_cannot_update_license(self):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(url_node, data, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_update_node_with_existing_license_year_attribute_only(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_year='2015'
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

    def test_update_node_with_existing_license_copyright_holders_attribute_only(
            self, user_admin_contrib, node, make_payload, make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update_node_with_existing_license_relationship_only(
            self, user_admin_contrib, node, make_payload,
            make_request, license_cc0, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
        )
        node.save()

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

    def test_update_node_with_existing_license_relationship_and_attributes(
            self, user_admin_contrib, node, make_payload, make_request,
            license_no, license_cc0, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2014',
                'copyrightHolders': ['Reason', 'Mr. E']
            },
            Auth(user_admin_contrib),
            save=True
        )

        assert node.node_license.node_license == license_no
        assert node.node_license.year == '2014'
        assert node.node_license.copyright_holders == ['Reason', 'Mr. E']

        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id,
            license_year='2015',
            copyright_holders=['Mr. Monument', 'Princess OSF']
        )

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.node_license.reload()

        assert node.node_license.node_license == license_cc0
        assert node.node_license.year == '2015'
        assert node.node_license.copyright_holders == [
            'Mr. Monument', 'Princess OSF']

    def test_update_node_license_without_required_year_in_payload(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            copyright_holders=['Rick', 'Morty']
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'year must be specified for this license'

    def test_update_node_license_without_license_id(
            self, node, make_payload, make_request, url_node, user_admin_contrib):
        data = make_payload(
            node_id=node._id,
            license_year='2015',
            copyright_holders=['Ben, Jerry']
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'License ID must be provided for a Node License.'

    def test_update_node_license_without_required_copyright_holders_in_payload_(
            self, user_admin_contrib, node, make_payload, make_request, license_no, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='1994'
        )

        res = make_request(
            url_node, data,
            auth=user_admin_contrib.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'copyrightHolders must be specified for this license'

    def test_update_node_license_adds_log(
            self, user_admin_contrib, node, make_payload,
            make_request, license_cc0, url_node):
        data = make_payload(
            node_id=node._id,
            license_id=license_cc0._id
        )
        logs_before_update = node.logs.count()

        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        assert res.status_code == 200
        node.reload()
        logs_after_update = node.logs.count()

        assert logs_before_update != logs_after_update
        assert node.logs.latest().action == 'license_changed'

    def test_update_node_license_without_change_does_not_add_log(
            self, user_admin_contrib, node, make_payload,
            make_request, license_no, url_node):
        node.set_node_license(
            {
                'id': license_no.license_id,
                'year': '2015',
                'copyrightHolders': ['Kim', 'Kanye']
            },
            auth=Auth(user_admin_contrib),
            save=True
        )

        before_num_logs = node.logs.count()
        before_update_log = node.logs.latest()

        data = make_payload(
            node_id=node._id,
            license_id=license_no._id,
            license_year='2015',
            copyright_holders=['Kanye', 'Kim']
        )
        res = make_request(url_node, data, auth=user_admin_contrib.auth)
        node.reload()

        after_num_logs = node.logs.count()
        after_update_log = node.logs.latest()

        assert res.status_code == 200
        assert before_num_logs == after_num_logs
        assert before_update_log._id == after_update_log._id
