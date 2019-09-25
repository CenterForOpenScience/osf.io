import mock
import pytest
import datetime

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.exceptions import UserNotAffiliatedError, DraftRegistrationStateError
from osf.models import RegistrationSchema, DraftRegistration, DraftRegistrationContributor, NodeLicense, Node
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.test_node import TestNodeEditableFieldsMixin, TestTagging, TestNodeLicenses, TestNodeSubjects
from tests.test_preprints import TestContributorMethods

from website import settings

from . import factories
pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return factories.UserFactory()

@pytest.fixture()
def project(user, auth, fake):
    ret = factories.ProjectFactory(creator=user)
    ret.add_tag(fake.word(), auth=auth)
    return ret

@pytest.fixture()
def auth(user):
    return Auth(user)

@pytest.fixture()
def draft_registration(project):
    return factories.DraftRegistrationFactory(branched_from=project)


class TestDraftRegistrations:
    # copied from tests/test_registrations/test_models.py
    def test_factory(self):
        draft = factories.DraftRegistrationFactory()
        assert draft.branched_from is not None
        assert draft.initiator is not None
        assert draft.registration_schema is not None

        user = factories.UserFactory()
        draft = factories.DraftRegistrationFactory(initiator=user)
        assert draft.initiator == user

        node = factories.ProjectFactory()
        draft = factories.DraftRegistrationFactory(branched_from=node)
        assert draft.branched_from == node
        assert draft.initiator == node.creator

        # Pick an arbitrary v2 schema
        schema = RegistrationSchema.objects.filter(schema_version=2).first()
        data = {'some': 'data'}
        draft = factories.DraftRegistrationFactory(registration_schema=schema, registration_metadata=data)
        assert draft.registration_schema == schema
        assert draft.registration_metadata == data

    @mock.patch('website.settings.ENABLE_ARCHIVER', False)
    def test_register(self):
        user = factories.UserFactory()
        auth = Auth(user)
        project = factories.ProjectFactory(creator=user)
        draft = factories.DraftRegistrationFactory(branched_from=project)
        assert not draft.registered_node
        draft.register(auth)
        assert draft.registered_node

        # group member with admin access cannot register
        member = factories.AuthUserFactory()
        osf_group = factories.OSFGroupFactory(creator=user)
        osf_group.make_member(member, auth=auth)
        project.add_osf_group(osf_group, ADMIN)
        draft_2 = factories.DraftRegistrationFactory(branched_from=project)
        assert project.has_permission(member, ADMIN)
        with pytest.raises(PermissionsError):
            draft_2.register(Auth(member))
        assert not draft_2.registered_node

    def test_update_metadata_tracks_changes(self, project):
        draft = factories.DraftRegistrationFactory(branched_from=project)

        draft.registration_metadata = {
            'foo': {
                'value': 'bar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True
            },
        }
        changes = draft.update_metadata({
            'foo': {
                'value': 'foobar',
            },
            'a': {
                'value': 1,
            },
            'b': {
                'value': True,
            },
            'c': {
                'value': 2,
            },
        })
        draft.save()
        for key in ['foo', 'c']:
            assert key in changes

    def test_has_active_draft_registrations(self):
        project, project2 = factories.ProjectFactory(), factories.ProjectFactory()
        factories.DraftRegistrationFactory(branched_from=project)
        assert project.has_active_draft_registrations is True
        assert project2.has_active_draft_registrations is False

    def test_draft_registrations_active(self):
        project = factories.ProjectFactory()
        registration = factories.RegistrationFactory(project=project)
        deleted_registration = factories.RegistrationFactory(project=project, is_deleted=True)
        draft = factories.DraftRegistrationFactory(branched_from=project, user=project.creator)
        draft2 = factories.DraftRegistrationFactory(branched_from=project, user=project.creator, registered_node=deleted_registration)
        finished_draft = factories.DraftRegistrationFactory(branched_from=project, user=project.creator, registered_node=registration)
        assert draft in project.draft_registrations_active.all()
        assert draft2 in project.draft_registrations_active.all()
        assert finished_draft in project.draft_registrations_active.all()

    def test_update_metadata_interleaves_comments_by_created_timestamp(self, project):
        draft = factories.DraftRegistrationFactory(branched_from=project)
        now = datetime.datetime.today()

        comments = []
        times = (now + datetime.timedelta(minutes=i) for i in range(6))
        for time in times:
            comments.append({
                'created': time.isoformat(),
                'value': 'Foo'
            })
        orig_data = {
            'foo': {
                'value': 'bar',
                'comments': [comments[i] for i in range(0, 6, 2)]
            }
        }
        draft.update_metadata(orig_data)
        draft.save()
        assert draft.registration_metadata['foo']['comments'] == [comments[i] for i in range(0, 6, 2)]

        new_data = {
            'foo': {
                'value': 'bar',
                'comments': [comments[i] for i in range(1, 6, 2)]
            }
        }
        draft.update_metadata(new_data)
        draft.save()
        assert draft.registration_metadata['foo']['comments'] == comments

    def test_draft_registration_url(self):
        project = factories.ProjectFactory()
        draft = factories.DraftRegistrationFactory(branched_from=project)

        assert draft.url == settings.DOMAIN + 'project/{}/drafts/{}'.format(project._id, draft._id)

    def test_create_from_node_existing(self, user):
        node = factories.ProjectFactory(creator=user)

        member = factories.AuthUserFactory()
        osf_group = factories.OSFGroupFactory(creator=user)
        osf_group.make_member(member, auth=Auth(user))
        node.add_osf_group(osf_group, ADMIN)

        write_contrib = factories.AuthUserFactory()
        subject = factories.SubjectFactory()
        institution = factories.InstitutionFactory()
        user.affiliated_institutions.add(institution)

        title = 'A Study of Elephants'
        description = 'Loxodonta africana'
        category = 'Methods and Materials'

        node.set_title(title, Auth(user))
        node.set_description(description, Auth(user))
        node.category = category
        node.add_contributor(write_contrib, permissions=WRITE)

        GPL3 = NodeLicense.objects.get(license_id='GPL3')
        NEW_YEAR = '2014'
        COPYLEFT_HOLDERS = ['Richard Stallman']
        node.set_node_license(
            {
                'id': GPL3.license_id,
                'year': NEW_YEAR,
                'copyrightHolders': COPYLEFT_HOLDERS
            },
            auth=Auth(user),
            save=True
        )
        node.add_tag('savanna', Auth(user))
        node.add_tag('taxonomy', Auth(user))
        node.set_subjects([[subject._id]], auth=Auth(node.creator))
        node.affiliated_institutions.add(institution)
        node.save()

        draft = DraftRegistration.create_from_node(
            node=node,
            user=user,
            schema=factories.get_default_metaschema(),
        )

        # Assert existing metadata-like node attributes are copied to the draft
        assert draft.title == title
        assert draft.description == description
        assert draft.category == category
        assert user in draft.contributors.all()
        assert write_contrib in draft.contributors.all()
        assert member not in draft.contributors.all()
        assert not draft.has_permission(member, 'read')

        assert draft.get_permissions(user) == [READ, WRITE, ADMIN]
        assert draft.get_permissions(write_contrib) == [READ, WRITE]

        assert draft.node_license.license_id == GPL3.license_id
        assert draft.node_license.name == GPL3.name
        assert draft.node_license.copyright_holders == COPYLEFT_HOLDERS

        draft_tags = draft.tags.values_list('name', flat=True)
        assert 'savanna' in draft_tags
        assert 'taxonomy' in draft_tags
        assert subject in draft.subjects.all()
        assert institution in draft.affiliated_institutions.all()
        assert draft.branched_from == node

    def test_create_from_node_draft_node(self, user):
        draft = DraftRegistration.create_from_node(
            user=user,
            schema=factories.get_default_metaschema(),
        )

        assert draft.title == 'Untitled'
        assert draft.description == ''
        assert draft.category == ''
        assert user in draft.contributors.all()
        assert len(draft.contributors.all()) == 1

        assert draft.get_permissions(user) == [READ, WRITE, ADMIN]

        assert draft.node_license is None

        draft_tags = draft.tags.values_list('name', flat=True)
        assert len(draft_tags) == 0
        assert draft.subjects.count() == 0
        assert draft.affiliated_institutions.count() == 0

    def test_branched_from_must_be_a_node_or_draft_node(self):
        with pytest.raises(DraftRegistrationStateError):
            DraftRegistration.create_from_node(
                user=user,
                node=factories.RegistrationFactory(),
                schema=factories.get_default_metaschema()
            )

        with pytest.raises(DraftRegistrationStateError):
            DraftRegistration.create_from_node(
                user=user,
                node=factories.CollectionFactory(),
                schema=factories.get_default_metaschema()
            )

    def test_can_view_property(self, user):
        project = factories.ProjectFactory(creator=user)

        write_contrib = factories.UserFactory()
        read_contrib = factories.UserFactory()
        non_contrib = factories.UserFactory()

        draft = DraftRegistration.create_from_node(
            user=user,
            node=project,
            schema=factories.get_default_metaschema()
        )
        project.add_contributor(non_contrib, ADMIN, save=True)
        draft.add_contributor(write_contrib, WRITE, save=True)
        draft.add_contributor(read_contrib, READ, save=True)

        assert draft.get_permissions(user) == [READ, WRITE, ADMIN]
        assert draft.get_permissions(write_contrib) == [READ, WRITE]
        assert draft.get_permissions(read_contrib) == [READ]

        assert draft.can_view(Auth(user)) is True
        assert draft.can_view(Auth(write_contrib)) is True
        assert draft.can_view(Auth(read_contrib)) is True

        assert draft.can_view(Auth(non_contrib)) is False


class TestSetDraftRegistrationEditableFields(TestNodeEditableFieldsMixin):
    @pytest.fixture()
    def resource(self, project):
        return factories.DraftRegistrationFactory(branched_from=project, title='That Was Then', description='A description')

    @pytest.fixture()
    def model(self):
        return DraftRegistration


class TestDraftRegistrationContributorMethods(TestContributorMethods):
    @pytest.fixture()
    def resource(self, project):
        return factories.DraftRegistrationFactory(branched_from=project, title='That Was Then', description='A description')

    @pytest.fixture()
    def contrib(self):
        return factories.UserFactory()

    @pytest.fixture()
    def contributor_model(self):
        return DraftRegistrationContributor

    @pytest.fixture()
    def make_resource_contributor(self, user, resource, visible=True):
        def make_contributor(user, resource, visible=True):
            contrib = DraftRegistrationContributor.objects.create(user=user, draft_registration=resource, visible=visible)
            return contrib
        return make_contributor

    @pytest.fixture()
    def contributor_exists(self, user, resource, visible=True):
        def query_contributor(user, resource, visible):
            contrib_exists = DraftRegistrationContributor.objects.filter(user=user, draft_registration=resource, visible=visible).exists()
            return contrib_exists
        return query_contributor


class TestDraftRegistrationAffiliatedInstitutions:
    def test_affiliated_institutions(self, draft_registration):
        inst1, inst2 = factories.InstitutionFactory(), factories.InstitutionFactory()
        user = draft_registration.initiator
        user.affiliated_institutions.add(inst1, inst2)
        draft_registration.add_affiliated_institution(inst1, user=user)

        assert inst1 in draft_registration.affiliated_institutions.all()
        assert inst2 not in draft_registration.affiliated_institutions.all()

        draft_registration.remove_affiliated_institution(inst1, user=user)

        assert inst1 not in draft_registration.affiliated_institutions.all()
        assert inst2 not in draft_registration.affiliated_institutions.all()

        user.affiliated_institutions.remove(inst1)

        with pytest.raises(UserNotAffiliatedError):
            draft_registration.add_affiliated_institution(inst1, user=user)


class TestDraftRegistrationTagging(TestTagging):
    @pytest.fixture()
    def node(self, user):
        # Overrides "node" resource on tag test, to make it a draft registration instead
        project = Node.objects.create(title='Project title', creator_id=user.id)
        return factories.DraftRegistrationFactory(branched_from=project)


class TestDraftRegistrationLicenses(TestNodeLicenses):
    @pytest.fixture()
    def node(self, draft_registration, node_license, user):
        # Overrides "node" resource to make it a draft registration instead
        draft_registration.node_license = factories.NodeLicenseRecordFactory(
            node_license=node_license,
            year=self.YEAR,
            copyright_holders=self.COPYRIGHT_HOLDERS
        )
        draft_registration.save()
        return draft_registration


class TestDraftRegistrationSubjects(TestNodeSubjects):
    @pytest.fixture()
    def project(self, draft_registration):
        # Overrides "project" resource to make it a draft registration instead
        return draft_registration

    @pytest.fixture()
    def subject(self):
        return factories.SubjectFactory()

    @pytest.fixture()
    def read_contrib(self, project):
        read_contrib = factories.AuthUserFactory()
        project.add_contributor(read_contrib, auth=Auth(project.creator), permissions=READ)
        project.save()
        return read_contrib

    def test_cannot_set_subjects(self, project, subject, read_contrib):
        initial_subjects = list(project.subjects.all())
        with pytest.raises(PermissionsError):
            project.set_subjects([[subject._id]], auth=Auth(read_contrib))

        project.reload()
        assert initial_subjects == list(project.subjects.all())
