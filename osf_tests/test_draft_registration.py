import mock
import pytest
import datetime

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.exceptions import UserNotAffiliatedError, DraftRegistrationStateError, NodeStateError
from osf.models import RegistrationSchema, DraftRegistration, DraftRegistrationContributor, NodeLicense, Node, NodeLog
from osf.utils.permissions import ADMIN, READ, WRITE
from osf_tests.test_node import TestNodeEditableFieldsMixin, TestTagging, TestNodeSubjects
from osf_tests.test_node_license import TestNodeLicenses

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

    @mock.patch('website.settings.ENABLE_ARCHIVER', False)
    def test_register_no_title_fails(self):
        user = factories.UserFactory()
        auth = Auth(user)
        project = factories.ProjectFactory(creator=user)
        draft = factories.DraftRegistrationFactory(branched_from=project)
        draft.title = ''
        draft.save()
        with pytest.raises(NodeStateError) as e:
            draft.register(auth)

        assert str(e.value) == 'Draft Registration must have title to be registered'

    def test_update_metadata_updates_registration_responses(self, project):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=2
        )
        draft = factories.DraftRegistrationFactory(registration_schema=schema, branched_from=project)
        new_metadata = {
            'looked': {
                'comments': [],
                'value': 'Yes',
                'extra': []
            },
            'datacompletion': {
                'comments': [],
                'value': 'No, data collection has not begun',
                'extra': []
            },
            'comments': {
                'comments': [],
                'value': '',
                'extra': []
            }
        }
        draft.update_metadata(new_metadata)
        draft.save()
        # To preserve both workflows, if update_metadata is called,
        # a flattened version of that metadata is stored in
        # registration_responses
        assert draft.registration_responses == {
            'looked': 'Yes',
            'datacompletion': 'No, data collection has not begun',
            'comments': ''
        }

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

    def test_update_registration_responses(self, project):
        schema = RegistrationSchema.objects.get(
            name='OSF-Standard Pre-Data Collection Registration',
            schema_version=2
        )
        draft = factories.DraftRegistrationFactory(registration_schema=schema, branched_from=project)
        registration_responses = {
            'looked': 'Yes',
            'datacompletion': 'No, data collection has not begun',
            'comments': ''
        }
        draft.update_registration_responses(registration_responses)
        draft.save()
        # To preserve both workflows, if update_metadata is called,
        # a flattened version of that metadata is stored in
        # registration_responses
        assert draft.registration_metadata == {
            'looked': {
                'comments': [],
                'value': 'Yes',
                'extra': []
            },
            'datacompletion': {
                'comments': [],
                'value': 'No, data collection has not begun',
                'extra': []
            },
            'comments': {
                'comments': [],
                'value': '',
                'extra': []
            }
        }

    def test_has_active_draft_registrations(self):
        project, project2 = factories.ProjectFactory(), factories.ProjectFactory()
        factories.DraftRegistrationFactory(branched_from=project)
        assert project.has_active_draft_registrations is True
        assert project2.has_active_draft_registrations is False

    def test_draft_registrations_active(self):
        project = factories.ProjectFactory()

        registration = factories.RegistrationFactory(project=project)
        deleted_registration = factories.RegistrationFactory(project=project)
        deleted_registration.is_deleted = True
        deleted_registration.save()

        draft = factories.DraftRegistrationFactory(branched_from=project, user=project.creator)

        draft2 = factories.DraftRegistrationFactory(branched_from=project, user=project.creator)
        draft2.registered_node = deleted_registration
        draft2.save()

        finished_draft = factories.DraftRegistrationFactory(branched_from=project, user=project.creator)
        finished_draft.registered_node = registration
        finished_draft.save()

        assert draft in project.draft_registrations_active.all()
        assert draft2 in project.draft_registrations_active.all()
        assert finished_draft not in project.draft_registrations_active.all()

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
        assert write_contrib not in draft.contributors.all()
        assert member not in draft.contributors.all()
        assert not draft.has_permission(member, 'read')

        assert draft.get_permissions(user) == [READ, WRITE, ADMIN]
        assert draft.get_permissions(write_contrib) == []

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


class TestDraftRegistrationContributorMethods():

    def test_add_contributor(self, draft_registration, user, auth):
        # A user is added as a contributor
        user = factories.UserFactory()
        draft_registration.add_contributor(contributor=user, auth=auth)
        draft_registration.save()
        assert draft_registration.is_contributor(user) is True
        assert draft_registration.has_permission(user, ADMIN) is False
        assert draft_registration.has_permission(user, WRITE) is True
        assert draft_registration.has_permission(user, READ) is True

        last_log = draft_registration.logs.all().order_by('-created')[0]
        assert last_log.action == 'contributor_added'
        assert last_log.params['contributors'] == [user._id]

    def test_add_contributors(self, draft_registration, auth):
        user1 = factories.UserFactory()
        user2 = factories.UserFactory()
        draft_registration.add_contributors(
            [
                {'user': user1, 'permissions': ADMIN, 'visible': True},
                {'user': user2, 'permissions': WRITE, 'visible': False}
            ],
            auth=auth
        )
        last_log = draft_registration.logs.all().order_by('-created')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )
        assert draft_registration.is_contributor(user1)
        assert draft_registration.is_contributor(user2)
        assert user1._id in draft_registration.visible_contributor_ids
        assert user2._id not in draft_registration.visible_contributor_ids
        assert draft_registration.get_permissions(user1) == [READ, WRITE, ADMIN]
        assert draft_registration.get_permissions(user2) == [READ, WRITE]
        last_log = draft_registration.logs.all().order_by('-created')[0]
        assert (
            last_log.params['contributors'] ==
            [user1._id, user2._id]
        )

    def test_cant_add_creator_as_contributor_twice(self, draft_registration, user):
        draft_registration.add_contributor(contributor=user)
        draft_registration.save()
        assert len(draft_registration.contributors) == 1

    def test_cant_add_same_contributor_twice(self, draft_registration):
        contrib = factories.UserFactory()
        draft_registration.add_contributor(contributor=contrib)
        draft_registration.save()
        draft_registration.add_contributor(contributor=contrib)
        draft_registration.save()
        assert len(draft_registration.contributors) == 2

    def test_remove_unregistered_conributor_removes_unclaimed_record(self, draft_registration, auth):
        new_user = draft_registration.add_unregistered_contributor(fullname='David Davidson',
            email='david@davidson.com', auth=auth)
        draft_registration.save()
        assert draft_registration.is_contributor(new_user)  # sanity check
        assert draft_registration._primary_key in new_user.unclaimed_records
        draft_registration.remove_contributor(
            auth=auth,
            contributor=new_user
        )
        draft_registration.save()
        new_user.refresh_from_db()
        assert draft_registration.is_contributor(new_user) is False
        assert draft_registration._primary_key not in new_user.unclaimed_records

    def test_is_contributor(self, draft_registration):
        contrib, noncontrib = factories.UserFactory(), factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=contrib, draft_registration=draft_registration)

        assert draft_registration.is_contributor(contrib) is True
        assert draft_registration.is_contributor(noncontrib) is False
        assert draft_registration.is_contributor(None) is False

    def test_visible_initiator(self, project, user):
        project_contributor = project.contributor_set.get(user=user)
        assert project_contributor.visible is True

        draft_reg = factories.DraftRegistrationFactory(branched_from=project, initiator=user)
        draft_reg_contributor = draft_reg.contributor_set.get(user=user)
        assert draft_reg_contributor.visible is True

    def test_non_visible_initiator(self, project, user):
        invisible_user = factories.UserFactory()
        project.add_contributor(contributor=invisible_user, permissions=ADMIN, visible=False)
        invisible_project_contributor = project.contributor_set.get(user=invisible_user)
        assert invisible_project_contributor.visible is False

        draft_reg = factories.DraftRegistrationFactory(branched_from=project, initiator=invisible_user)
        invisible_draft_reg_contributor = draft_reg.contributor_set.get(user=invisible_user)
        assert invisible_draft_reg_contributor.visible is False

    def test_visible_contributor_ids(self, draft_registration, user):
        visible_contrib = factories.UserFactory()
        invisible_contrib = factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=visible_contrib, draft_registration=draft_registration, visible=True)
        DraftRegistrationContributor.objects.create(user=invisible_contrib, draft_registration=draft_registration, visible=False)
        assert visible_contrib._id in draft_registration.visible_contributor_ids
        assert invisible_contrib._id not in draft_registration.visible_contributor_ids

    def test_visible_contributors(self, draft_registration, user):
        visible_contrib = factories.UserFactory()
        invisible_contrib = factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=visible_contrib, draft_registration=draft_registration, visible=True)
        DraftRegistrationContributor.objects.create(user=invisible_contrib, draft_registration=draft_registration, visible=False)
        assert visible_contrib in draft_registration.visible_contributors
        assert invisible_contrib not in draft_registration.visible_contributors

    def test_set_visible_false(self, draft_registration, auth):
        contrib = factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=contrib, draft_registration=draft_registration, visible=True)
        draft_registration.set_visible(contrib, visible=False, auth=auth)
        draft_registration.save()
        assert DraftRegistrationContributor.objects.filter(user=contrib, draft_registration=draft_registration, visible=False).exists() is True

        last_log = draft_registration.logs.all().order_by('-created')[0]
        assert last_log.user == auth.user
        assert last_log.action == NodeLog.MADE_CONTRIBUTOR_INVISIBLE

    def test_set_visible_true(self, draft_registration, auth):
        contrib = factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=contrib, draft_registration=draft_registration, visible=False)
        draft_registration.set_visible(contrib, visible=True, auth=auth)
        draft_registration.save()
        assert DraftRegistrationContributor.objects.filter(user=contrib, draft_registration=draft_registration, visible=True).exists() is True

        last_log = draft_registration.logs.all().order_by('-created')[0]
        assert last_log.user == auth.user
        assert last_log.action == NodeLog.MADE_CONTRIBUTOR_VISIBLE

    def test_set_visible_is_noop_if_visibility_is_unchanged(self, draft_registration, auth):
        visible, invisible = factories.UserFactory(), factories.UserFactory()
        DraftRegistrationContributor.objects.create(user=visible, draft_registration=draft_registration, visible=True)
        DraftRegistrationContributor.objects.create(user=invisible, draft_registration=draft_registration, visible=False)
        original_log_count = draft_registration.logs.count()
        draft_registration.set_visible(invisible, visible=False, auth=auth)
        draft_registration.set_visible(visible, visible=True, auth=auth)
        draft_registration.save()
        assert draft_registration.logs.count() == original_log_count

    def test_set_visible_contributor_with_only_one_contributor(self, draft_registration, user):
        with pytest.raises(ValueError) as excinfo:
            draft_registration.set_visible(user=user, visible=False, auth=None)
        assert str(excinfo.value) == 'Must have at least one visible contributor'

    def test_set_visible_missing(self, draft_registration):
        with pytest.raises(ValueError):
            draft_registration.set_visible(factories.UserFactory(), True)

    def test_remove_contributor(self, draft_registration, auth):
        # A user is added as a contributor
        user2 = factories.UserFactory()
        draft_registration.add_contributor(contributor=user2, auth=auth, save=True)
        assert user2 in draft_registration.contributors
        assert draft_registration.has_permission(user2, WRITE)
        # The user is removed
        draft_registration.remove_contributor(auth=auth, contributor=user2)
        draft_registration.reload()

        assert user2 not in draft_registration.contributors
        assert draft_registration.get_permissions(user2) == []
        assert draft_registration.logs.latest().action == 'contributor_removed'
        assert draft_registration.logs.latest().params['contributors'] == [user2._id]

    def test_remove_contributors(self, draft_registration, auth):
        user1 = factories.UserFactory()
        user2 = factories.UserFactory()
        draft_registration.add_contributors(
            [
                {'user': user1, 'permissions': WRITE, 'visible': True},
                {'user': user2, 'permissions': WRITE, 'visible': True}
            ],
            auth=auth
        )
        assert user1 in draft_registration.contributors
        assert user2 in draft_registration.contributors
        assert draft_registration.has_permission(user1, WRITE)
        assert draft_registration.has_permission(user2, WRITE)

        draft_registration.remove_contributors(auth=auth, contributors=[user1, user2], save=True)
        draft_registration.reload()

        assert user1 not in draft_registration.contributors
        assert user2 not in draft_registration.contributors
        assert draft_registration.get_permissions(user1) == []
        assert draft_registration.get_permissions(user2) == []
        assert draft_registration.logs.latest().action == 'contributor_removed'

    def test_replace_contributor(self, draft_registration):
        contrib = factories.UserFactory()
        draft_registration.add_contributor(contrib, auth=Auth(draft_registration.creator))
        draft_registration.save()
        assert contrib in draft_registration.contributors.all()  # sanity check
        replacer = factories.UserFactory()
        old_length = draft_registration.contributors.count()
        draft_registration.replace_contributor(contrib, replacer)
        draft_registration.save()
        new_length = draft_registration.contributors.count()
        assert contrib not in draft_registration.contributors.all()
        assert replacer in draft_registration.contributors.all()
        assert old_length == new_length

        # test unclaimed_records is removed
        assert (
            draft_registration._id not in
            contrib.unclaimed_records.keys()
        )

    def test_permission_override_fails_if_no_admins(self, draft_registration, user):
        # User has admin permissions because they are the creator
        # Cannot lower permissions
        with pytest.raises(DraftRegistrationStateError):
            draft_registration.add_contributor(user, permissions=WRITE)

    def test_update_contributor(self, draft_registration, auth):
        new_contrib = factories.AuthUserFactory()
        draft_registration.add_contributor(new_contrib, permissions=WRITE, auth=auth)

        assert draft_registration.get_permissions(new_contrib) == [READ, WRITE]
        assert draft_registration.get_visible(new_contrib) is True

        draft_registration.update_contributor(
            new_contrib,
            READ,
            False,
            auth=auth
        )
        assert draft_registration.get_permissions(new_contrib) == [READ]
        assert draft_registration.get_visible(new_contrib) is False

    def test_update_contributor_non_admin_raises_error(self, draft_registration, auth):
        non_admin = factories.AuthUserFactory()
        draft_registration.add_contributor(
            non_admin,
            permissions=WRITE,
            auth=auth
        )
        with pytest.raises(PermissionsError):
            draft_registration.update_contributor(
                non_admin,
                None,
                False,
                auth=Auth(non_admin)
            )

    def test_update_contributor_only_admin_raises_error(self, draft_registration, auth):
        with pytest.raises(DraftRegistrationStateError):
            draft_registration.update_contributor(
                auth.user,
                WRITE,
                True,
                auth=auth
            )

    def test_update_contributor_non_contrib_raises_error(self, draft_registration, auth):
        non_contrib = factories.AuthUserFactory()
        with pytest.raises(ValueError):
            draft_registration.update_contributor(
                non_contrib,
                ADMIN,
                True,
                auth=auth
            )


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
