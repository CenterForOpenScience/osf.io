from unittest import mock

from django.core.exceptions import MultipleObjectsReturned
import pytest

from framework.auth import Auth
from api_tests.utils import create_test_file
from osf.models import AbstractNode, Guid, GuidVersionsThrough, NodeLicenseRecord, OSFUser, Preprint
from osf.models.base import (
    VersionedGuidMixin,
    coerce_guid,
    guid_redirect_automatically,
    guid_redirect_url,
    redirect_guid,
)
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    NodeLicenseRecordFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
    RegistrationFactory,
    UserFactory,
)
from tests.base import OsfTestCase


@pytest.mark.django_db
class TestGuid:

    def test_long_id_gets_generated_on_creation(self):
        obj = NodeLicenseRecordFactory()
        assert obj._id
        assert len(obj._id) > 5

    def test_loading_by_object_id(self):
        obj = NodeLicenseRecordFactory()
        assert NodeLicenseRecord.load(obj._id) == obj

    def test_loading_by_short_guid(self):
        obj = UserFactory()
        assert OSFUser.load(obj._id) == obj

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory,
        RegistrationFactory,
    ])
    def test_short_guid_gets_generated_on_creation(self, Factory):
        obj = Factory()
        assert obj._id
        assert len(obj._id) == 5


@pytest.mark.django_db
class TestReferent:

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent(self, Factory):
        obj = Factory()
        guid = Guid.objects.get(_id=obj._id)
        assert guid.referent == obj

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory
    ])
    def test_referent_can_be_set(self, Factory):
        obj = Factory()
        obj1 = Factory()

        guid = Guid.load(obj._id)
        assert guid.referent == obj  # sanity check

        guid.referent = obj1
        assert guid.referent == obj1

    @pytest.mark.skip('I don\'t actually think we do this anywhere')
    def test_swapping_guids(self):
        user = UserFactory()
        node = NodeFactory()

        user_guid = user.guids[0]
        node_guid = node.guids[0]

        user._id = node_guid._id
        node._id = user_guid._id

        assert node_guid._id == user._id
        assert user_guid._id == node._id

    def test_id_matches(self):
        user = UserFactory()
        guid = Guid.objects.get(_id=user._id)

        assert user._id == guid._id

    @pytest.mark.skip('I don\'t actually think we do this anywhere')
    @pytest.mark.parametrize('Factory',
     [
         UserFactory,
         NodeFactory
     ])
    def test_nulling_out_guid(self, Factory):
        obj = Factory()

        guid = Guid.load(obj._id)

        obj.guid = None

        obj.save()
        obj.refresh_from_db()

        # queryset cache returns the old version
        guid.refresh_from_db()

        assert obj.guid != guid

        assert guid.guid != obj.guid.guid

    @pytest.mark.parametrize('Factory',
    [
        UserFactory,
        NodeFactory,
    ])
    def test_querying_with_multiple_guids(self, Factory):

        obj = Factory()
        guids = [obj.guids.first()]

        for i in range(0, 16):
            guids.append(Guid.objects.create(referent=obj))

        try:
            Factory._meta.model.objects.get(id=obj.id)
        except MultipleObjectsReturned as ex:
            pytest.fail(f'Multiple objects returned for {Factory._meta.model} with multiple guids. {ex}')


@pytest.mark.enable_bookmark_creation
class TestResolveGuid(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.node = NodeFactory()

    def test_resolve_guid(self):
        with mock.patch('framework.csrf.handlers.get_current_user_id', return_value=self.node.creator_id):
            res_guid = self.app.get(self.node.web_url_for('node_setting', _guid=True), auth=self.node.creator.auth)
            res_full = self.app.get(self.node.web_url_for('node_setting'), auth=self.node.creator.auth)
        assert res_guid.text == res_full.text

    def test_resolve_guid_no_referent(self):
        guid = Guid.load(self.node._id)
        guid.referent = None
        guid.save()
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
        )
        assert res.status_code == 404

    @mock.patch('osf.models.node.Node.deep_url', None)
    def test_resolve_guid_no_url(self):
        res = self.app.get(
            self.node.web_url_for('node_setting', _guid=True),
            auth=self.node.creator.auth,
        )
        assert res.status_code == 404

    def test_resolve_guid_no_auth_redirect_to_cas_includes_public(self):
        """
        Unauthenticated users are sent to login when visiting private projects, but not if the projects are public.
        """
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
        )
        assert res.status_code == 302
        assert '/login?service=' in res.location

        self.node.is_public = True
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
        )
        assert res.status_code == 200

    def test_resolve_guid_no_auth_redirect_to_cas_includes_public_with_url_segments(self):
        """
        Unauthenticated users are sent to login when visiting private projects related URLs, but not if the projects are
        public
        """
        for segment in ('comments', 'links', 'components', 'files', 'files/osfstorage', 'files/addon'):
            self.node.is_public = False
            self.node.save()
            res = self.app.get(
                f'{self.node.web_url_for("resolve_guid", guid=self.node._id)}/{segment}/',
            )
            assert res.status_code == 302
            assert '/login?service=' in res.location

            self.node.is_public = True
            self.node.save()
            res = self.app.get(
                f'{self.node.web_url_for("resolve_guid", guid=self.node._id)}/{segment}/',
            )
            assert res.status_code == 200

    def test_resolve_guid_private_request_access_or_redirect_to_cas(self):
        """
        Authenticated users are sent to the request access page when it is set to true on the node; otherwise, they get a
        legacy Forbidden page.
        """
        non_contrib = AuthUserFactory()
        self.node.access_requests_enabled = False
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
            auth=non_contrib.auth,
        )
        assert '<title>OSF | Forbidden</title>' in res.text
        assert res.status_code == 403

        self.node.access_requests_enabled = True
        self.node.save()
        res = self.app.get(
            self.node.web_url_for('resolve_guid', guid=self.node._id),
            auth=non_contrib.auth,
        )
        assert res.status_code == 403
        assert '<title>OSF | Request Access</title>' in res.text

    def test_resolve_guid_redirect_to_versioned_guid(self):
        pp = PreprintFactory(filename='test.pdf', finish=True)

        res = self.app.get(f'{pp.get_guid()._id}/')
        assert res.status_code == 302
        assert res.location == f'/{pp._id}/'

@pytest.fixture()
def creator():
    return AuthUserFactory()

@pytest.fixture()
def auth(creator):
    return Auth(user=creator)

@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory()


@pytest.mark.django_db
class TestGuidVersionsThrough:
    def test_creation_versioned_guid(self, creator, preprint_provider):
        preprint = Preprint.create(
            creator=creator,
            provider=preprint_provider,
            title='Preprint',
            description='Abstract'
        )
        assert preprint.guids.count() == 1
        assert preprint.creator == creator
        assert preprint.provider == preprint_provider
        assert preprint.title == 'Preprint'
        assert preprint.description == 'Abstract'

        preprint_guid = preprint.guids.first()
        assert preprint_guid.referent == preprint
        assert preprint_guid.content_type.model == 'preprint'
        assert preprint_guid.object_id == preprint.pk
        assert preprint_guid.is_versioned is True

        version_entry = preprint.versioned_guids.first()
        assert version_entry.guid == preprint_guid
        assert version_entry.referent == preprint
        assert version_entry.content_type.model == 'preprint'
        assert version_entry.object_id == preprint.pk
        assert version_entry.version == 1

    def test_create_version(self, creator, preprint_provider):
        preprint = PreprintFactory(creator=creator)
        assert preprint.guids.count() == 1
        preprint_guid = preprint.guids.first()

        preprint_metadata = {
            'subjects': [el for el in preprint.subjects.all().values_list('_id', flat=True)],
            'original_publication_date': preprint.original_publication_date,
            'custom_publication_citation': preprint.custom_publication_citation,
            'article_doi': preprint.article_doi,
            'has_coi': preprint.has_coi,
            'conflict_of_interest_statement': preprint.conflict_of_interest_statement,
            'has_data_links': preprint.has_data_links,
            'why_no_data': preprint.why_no_data,
            'data_links': preprint.data_links,
            'has_prereg_links': preprint.has_prereg_links,
            'why_no_prereg': preprint.why_no_prereg,
            'prereg_links': preprint.prereg_links,
        }
        if preprint.node:
            preprint_metadata['node'] = preprint.node
        if preprint.license:
            preprint_metadata['license_type'] = preprint.license.node_license
            preprint_metadata['license'] = {
                'copyright_holders': preprint.license.copyright_holders,
                'year': preprint.license.year
            }
        auth = Auth(user=creator)
        new_preprint, data_for_update = Preprint.create_version(create_from_guid=preprint._id, auth=auth)
        tags = data_for_update.pop('tags')
        assert list(tags) == list(preprint.tags.all().values_list('name', flat=True))
        assert preprint_metadata == data_for_update

        new_version = new_preprint.versioned_guids.first()

        assert preprint.guids.count() == 0
        assert preprint.versioned_guids.count() == 1
        assert preprint.files.count() == 1
        assert new_preprint.guids.count() == 1
        assert new_preprint.versioned_guids.count() == 1
        assert new_preprint.files.count() == 0

        assert new_version.referent == new_preprint
        assert new_version.object_id == new_preprint.pk
        assert new_version.content_type.model == 'preprint'
        assert new_version.guid == preprint_guid
        assert new_version.version == 2
        assert preprint_guid.versions.count() == 2

    def test_versioned_preprint_id_property(self, creator, preprint_provider):
        preprint = Preprint.create(
            creator=creator,
            provider=preprint_provider,
            title='Preprint',
            description='Abstract'
        )
        preprint_guid = preprint.guids.first()
        expected_guid = f'{preprint_guid._id}{VersionedGuidMixin.GUID_VERSION_DELIMITER}{VersionedGuidMixin.INITIAL_VERSION_NUMBER}'
        assert preprint._id == expected_guid

        GuidVersionsThrough.objects.filter(guid=preprint_guid).delete()
        preprint._id = None
        assert preprint._id is None


@pytest.mark.django_db
class TestGuidRedirect:
    """the url a guid redirects to: its own, else the one of the item it is part of
    (a file's target, a component's root)
    """
    URL = 'https://example.com/new-home'
    OTHER_URL = 'https://example.com/other-home'

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def component(self, project, user):
        return NodeFactory(parent=project, creator=user)

    @pytest.fixture()
    def grandchild(self, component, user):
        return NodeFactory(parent=component, creator=user)

    def set_redirect(self, osf_item, url=URL, automatically=False):
        guid = coerce_guid(osf_item)
        guid.redirect_url = url
        guid.redirect_automatically = automatically
        guid.save()

    @staticmethod
    def reloaded(osf_item):
        return type(osf_item).objects.get(pk=osf_item.pk)

    def test_no_redirect(self, project, component, grandchild):
        for item in (project, component, grandchild):
            assert redirect_guid(item) is None
            assert guid_redirect_url(item) is None
            assert guid_redirect_automatically(item) is False

    def test_own_redirect(self, project):
        self.set_redirect(project, automatically=True)
        assert redirect_guid(project) == coerce_guid(project)
        assert guid_redirect_url(project) == self.URL
        assert guid_redirect_automatically(project) is True

    def test_components_inherit_from_root(self, project, component, grandchild):
        self.set_redirect(project, automatically=True)
        for item in map(self.reloaded, (component, grandchild)):
            assert guid_redirect_url(item) == self.URL
            assert guid_redirect_automatically(item) is True

    def test_component_own_redirect_wins(self, project, component, grandchild):
        self.set_redirect(project, automatically=True)
        self.set_redirect(component, self.OTHER_URL)
        component, grandchild = map(self.reloaded, (component, grandchild))
        assert guid_redirect_url(component) == self.OTHER_URL
        assert guid_redirect_automatically(component) is False
        assert guid_redirect_url(grandchild) == self.URL

    def test_root_does_not_inherit_from_component(self, project, component):
        self.set_redirect(component)
        assert guid_redirect_url(self.reloaded(project)) is None

    def test_accepts_guid(self, project, component):
        self.set_redirect(project)
        assert guid_redirect_url(coerce_guid(self.reloaded(component))) == self.URL

    def test_file_inherits_from_node(self, project, user):
        file = create_test_file(project, user, filename='a.txt')
        self.set_redirect(project, automatically=True)
        file = self.reloaded(file)
        assert guid_redirect_url(file) == self.URL
        assert guid_redirect_automatically(file) is True

    def test_file_in_component_inherits_from_root(self, project, component, user):
        file = create_test_file(component, user, filename='a.txt')
        self.set_redirect(project)
        assert guid_redirect_url(self.reloaded(file)) == self.URL

    def test_file_own_redirect_wins(self, project, user):
        file = create_test_file(project, user, filename='a.txt')
        self.set_redirect(project)
        self.set_redirect(file, self.OTHER_URL)
        assert guid_redirect_url(self.reloaded(file)) == self.OTHER_URL

    def test_file_without_guid_inherits(self, project, user):
        file = create_test_file(project, user, filename='a.txt', create_guid=False)
        assert guid_redirect_url(self.reloaded(file)) is None
        self.set_redirect(project)
        assert guid_redirect_url(self.reloaded(file)) == self.URL

    def test_preprint(self, user):
        preprint = PreprintFactory(creator=user)
        assert guid_redirect_url(preprint) is None
        self.set_redirect(preprint)
        assert guid_redirect_url(preprint) == self.URL

    def test_soft_deleted_node_keeps_redirect(self, project, component):
        self.set_redirect(project)
        AbstractNode.objects.filter(pk=project.pk).update(is_deleted=True)  # marked as deleted, still in the db
        assert guid_redirect_url(self.reloaded(project)) == self.URL
        assert guid_redirect_url(self.reloaded(component)) == self.URL
