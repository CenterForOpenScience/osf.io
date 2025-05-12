from django.utils import timezone
from urllib.parse import urlparse
from unittest import mock
import pytest

from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.base.settings.defaults import API_BASE
from api.taxonomies.serializers import subjects_as_relationships_version
from framework.auth.core import Auth
from osf.utils import permissions
from osf_tests.factories import (
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    PrivateLinkFactory,
    PreprintFactory,
    ForkFactory,
    OSFGroupFactory,
    WithdrawnRegistrationFactory,
    DraftNodeFactory,
)


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
        return f'/{API_BASE}nodes/{project_public._id}/'

    @pytest.fixture()
    def url_private(self, project_private):
        return f'/{API_BASE}nodes/{project_private._id}/'

    @pytest.fixture()
    def url_component_public(self, component_public):
        return f'/{API_BASE}nodes/{component_public._id}/'

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
        draft_node_url = f'/{API_BASE}nodes/{draft_node._id}/'
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
        assert res.json['data']['attributes']['current_user_permissions'] == permissions_write

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
        expected_url = f'{url_public}children/'
        assert urlparse(url).path == expected_url

    #   test_node_has_contributors_link
        url = res.json['data']['relationships']['contributors']['links']['related']['href']
        expected_url = f'{url_public}contributors/'
        assert urlparse(url).path == expected_url

    #   test_node_has_node_links_link
        url = res.json['data']['relationships']['node_links']['links']['related']['href']
        expected_url = f'{url_public}node_links/'
        assert urlparse(url).path == expected_url

    #   test_node_has_registrations_link
        url = res.json['data']['relationships']['registrations']['links']['related']['href']
        expected_url = f'{url_public}registrations/'
        assert urlparse(url).path == expected_url

    #   test_node_has_files_link
        url = res.json['data']['relationships']['files']['links']['related']['href']
        expected_url = f'{url_public}files/'
        assert urlparse(url).path == expected_url

    #   test_node_has_affiliated_institutions_link_and_it_doesn't_serialize_to_none
        assert project_public.affiliated_institutions.count() == 0
        related_url = res.json['data']['relationships']['affiliated_institutions']['links']['related']['href']
        expected_url = f'{url_public}institutions/'
        assert urlparse(related_url).path == expected_url
        self_url = res.json['data']['relationships']['affiliated_institutions']['links']['self']['href']
        expected_url = f'{url_public}relationships/institutions/'
        assert urlparse(self_url).path == expected_url

    #   test_node_has_subjects_links_for_later_versions
        res = app.get(url_public + f'?version={subjects_as_relationships_version}')
        related_url = res.json['data']['relationships']['subjects']['links']['related']['href']
        expected_url = f'{url_public}subjects/'
        assert urlparse(related_url).path == expected_url
        self_url = res.json['data']['relationships']['subjects']['links']['self']['href']
        expected_url = f'{url_public}relationships/subjects/'
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
            f'{url_public}?related_counts=True',
            auth=user.auth)
        unread = res.json['data']['relationships']['comments']['links']['related']['meta']['unread']
        unread_comments_node = unread['node']
        assert unread_comments_node == 1

    def test_node_has_correct_wiki_page_count(self, user, app, url_private, project_private):
        res = app.get(f'{url_private}?related_counts=True', auth=user.auth)
        assert res.json['data']['relationships']['wikis']['links']['related']['meta']['count'] == 0

        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki_page = WikiFactory(node=project_private, user=user)
            WikiVersionFactory(wiki_page=wiki_page)

        res = app.get(f'{url_private}?related_counts=True', auth=user.auth)
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
            f'/{API_BASE}nodes/{folder._id}/',
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
            f'/{API_BASE}nodes/{folder._id}/',
            auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_node_list_embed_identifier_link(self, app, user, project_public, url_public):
        url = url_public + '?embed=identifiers'
        res = app.get(url)
        assert res.status_code == 200
        link = res.json['data']['relationships']['identifiers']['links']['related']['href']
        assert f'{url_public}identifiers/' in link

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

        log_date = timezone.now()
        project_private.deleted_date = log_date
        project_private.deleted = log_date
        project_private.is_deleted = True
        project_private.save()
        registration.reload()
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
        comp_url = f'/{API_BASE}nodes/{comp._id}/?version=2.11'
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
        comp_url = f'/{API_BASE}nodes/{comp._id}/?version=2.11'
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

    def test_current_user_permissions_vol(self, app, user, url_public, project_public):
        '''
        User's including view only link query params should get ONLY read permissions even if they are admins etc.
        '''
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(project_public)
        private_link.save()
        res = app.get(f'{url_public}?view_only={private_link.key}', auth=user.auth)
        assert [permissions.READ] == res.json['data']['attributes']['current_user_permissions']
