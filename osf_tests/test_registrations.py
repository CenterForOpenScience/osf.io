import mock
import pytest
import datetime

from django.utils import timezone
from framework.auth.core import Auth
from osf.models import Node, Registration, Sanction, MetaSchema, NodeLog
from addons.wiki.models import NodeWikiPage
from osf.modm_compat import Q

from website import settings
from website.project.model import ensure_schemas
from website.util.permissions import READ, WRITE, ADMIN

from . import factories
from .utils import assert_datetime_equal, mock_archive
from .factories import get_default_metaschema
from addons.wiki.tests.factories import NodeWikiFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _ensure_schemas(patched_models):
    return ensure_schemas()


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


# copied from tests/test_models.py
def test_factory(user, project):
    # Create a registration with kwargs
    registration1 = factories.RegistrationFactory(
        title='t1', description='d1', creator=user,
    )
    assert registration1.title == 't1'
    assert registration1.description == 'd1'
    assert registration1.contributors.count() == 1
    assert user in registration1.contributors.all()
    assert registration1.registered_user == user
    assert registration1.private_links.count() == 0

    # Create a registration from a project
    user2 = factories.UserFactory()
    project.add_contributor(user2)
    registration2 = factories.RegistrationFactory(
        project=project,
        user=user2,
        data={'some': 'data'},
    )
    assert registration2.registered_from == project
    assert registration2.registered_user == user2
    assert (
        registration2.registered_meta[get_default_metaschema()._id] ==
        {'some': 'data'}
    )


# copied from tests/test_models.py
class TestRegisterNode:

    @pytest.fixture()
    def registration(self, project):
        reg = factories.RegistrationFactory(project=project)
        private_link = factories.PrivateLinkFactory()
        private_link.nodes.add(reg)
        private_link.save()
        return reg

    def test_does_not_have_addon_added_log(self, registration):
        # should not have addon_added log from wiki addon being added
        assert NodeLog.ADDON_ADDED not in list(registration.logs.values_list('action', flat=True))

    def test_title(self, registration, project):
        assert registration.title == project.title

    def test_description(self, registration, project):
        assert registration.description == project.description

    def test_category(self, registration, project):
        assert registration.category == project.category

    def test_permissions(self, registration, project):
        assert registration.is_public is False
        project.set_privacy(Node.PUBLIC)
        registration = factories.RegistrationFactory(project=project)
        assert registration.is_public is False

    def test_contributors(self, registration, project):
        assert registration.contributors.count() == project.contributors.count()
        assert (
            set(registration.contributors.values_list('id', flat=True)) ==
            set(project.contributors.values_list('id', flat=True))
        )

    def test_forked_from(self, registration, project, auth):
        # A a node that is not a fork
        assert registration.forked_from is None
        # A node that is a fork
        fork = project.fork_node(auth)
        registration = factories.RegistrationFactory(project=fork)
        assert registration.forked_from == project

    def test_private_links(self, registration, project):
        assert registration.private_links != project.private_links

    def test_creator(self, registration, project, user):
        user2 = factories.UserFactory()
        project.add_contributor(user2)
        registration = factories.RegistrationFactory(project=project)
        assert registration.creator == user

    def test_logs(self, registration, project):
        # Registered node has all logs except for registration approval initiated
        assert project.logs.count() - 1 == registration.logs.count()
        assert project.logs.first().action == 'registration_initiated'
        project_second_log = project.logs.limit(2)[1]
        assert registration.logs.first().action == project_second_log.action

    def test_tags(self, registration, project):
        assert (
            set(registration.tags.values_list('name', flat=True)) ==
            set(project.tags.values_list('name', flat=True))
        )

    def test_nodes(self, project, user):

        # Create some nodes
        # component of project
        factories.NodeFactory(
            creator=user,
            parent=project,
            title='Title1',
        )
        subproject = factories.ProjectFactory(
            creator=user,
            parent=project,
            title='Title2',
        )
        # component of subproject
        factories.NodeFactory(
            creator=user,
            parent=subproject,
            title='Title3',
        )

        # Make a registration
        registration = factories.RegistrationFactory(project=project)

        # Reload the registration; else test won't catch failures to save
        registration.refresh_from_db()

        # Registration has the nodes
        assert registration._nodes.count() == 2
        assert(
            set(registration._nodes.values_list('title', flat=True)) ==
            set(project._nodes.values_list('title', flat=True))
        )
        # Nodes are copies and not the original versions
        for node in registration._nodes.all():
            assert node not in project._nodes.all()
            assert node.is_registration

    def test_linked_nodes(self, project, user, auth):
        linked_node = factories.ProjectFactory()
        project.add_node_link(linked_node, auth=auth, save=True)

        registration = factories.RegistrationFactory(project=project)
        registration.refresh_from_db()

        assert project.linked_nodes.count() == registration.linked_nodes.count()
        assert project.linked_nodes.first().title == registration.linked_nodes.first().title

    def test_private_contributor_registration(self, project, user):

        # Create some nodes
        # component
        comp1 = factories.NodeFactory(  # noqa
            title='Comp1',
            creator=user,
            parent=project,
        )
        # subproject
        comp2 = factories.ProjectFactory(  # noqa
            title='Comp1',
            creator=user,
            parent=project,
        )

        # Create some nodes to share
        shared_component = factories.NodeFactory(
            title='Shared Component',
            creator=user,
            parent=project,
        )
        shared_subproject = factories.ProjectFactory(
            title='Shared Subproject',
            creator=user,
            parent=project,
        )

        # Share the project and some nodes
        user2 = factories.UserFactory()
        project.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        shared_component.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        shared_subproject.add_contributor(user2, permissions=(READ, WRITE, ADMIN))

        # Partial contributor registers the node
        registration = factories.RegistrationFactory(project=project, user=user2)

        # The correct subprojects were registered
        for registered_node in registration._nodes.all():
            assert registered_node.root == registration
            assert registered_node.registered_from
            assert registered_node.parent_node == registration
            assert registered_node.registered_from.parent_node == project

    def test_is_registration(self, registration):
        assert registration.is_registration

    def test_registered_date(self, registration):
        assert_datetime_equal(registration.registered_date, timezone.now(), allowance=3000)

    def test_registered_addons(self, registration):
        assert (
            [addon.config.short_name for addon in registration.get_addons()] ==
            [addon.config.short_name for addon in registration.registered_from.get_addons()]
        )

    def test_registered_user(self, project):
        # Add a second contributor
        user2 = factories.UserFactory()
        project.add_contributor(user2, permissions=(READ, WRITE, ADMIN))
        # Second contributor registers project
        registration = factories.RegistrationFactory(parent=project, user=user2)
        assert registration.registered_user == user2

    def test_registered_from(self, registration, project):
        assert registration.registered_from == project

    def test_registered_get_absolute_url(self, registration):
        assert (
            registration.get_absolute_url() ==
            '{}v2/registrations/{}/'.format(settings.API_DOMAIN, registration._id)
        )

    def test_registration_list(self, registration, project):
        assert registration._id in [n._id for n in project.registrations_all]

    def test_registration_gets_institution_affiliation(self, user):
        node = factories.NodeFactory()
        institution = factories.InstitutionFactory()

        user.affiliated_institutions.add(institution)
        user.save()

        node.add_affiliated_institution(institution, user=user)
        node.save()

        registration = factories.RegistrationFactory(project=node)
        assert (
            set(registration.affiliated_institutions.values_list('id', flat=True)) ==
            set(node.affiliated_institutions.values_list('id', flat=True))
        )

    def test_registration_of_project_with_no_wiki_pages(self, registration):
        assert registration.wiki_pages_versions == {}
        assert registration.wiki_pages_current == {}
        assert registration.wiki_private_uuids == {}

    @mock.patch('website.project.signals.after_create_registration')
    def test_registration_clones_project_wiki_pages(self, mock_signal, project, user):
        project = factories.ProjectFactory(creator=user, is_public=True)
        wiki = NodeWikiFactory(node=project)
        current_wiki = NodeWikiFactory(node=project, version=2)
        registration = project.register_node(get_default_metaschema(), Auth(user), '', None)
        assert registration.wiki_private_uuids == {}

        registration_wiki_current = NodeWikiPage.load(registration.wiki_pages_current[current_wiki.page_name])
        assert registration_wiki_current.node == registration
        assert registration_wiki_current._id != current_wiki._id

        registration_wiki_version = NodeWikiPage.load(registration.wiki_pages_versions[wiki.page_name][0])
        assert registration_wiki_version.node == registration
        assert registration_wiki_version._id != wiki._id

    def test_legacy_private_registrations_can_be_made_public(self, registration, auth):
        registration.is_public = False
        registration.set_privacy(Node.PUBLIC, auth=auth)
        assert registration.is_public


# copied from tests/test_registrations
class TestNodeSanctionStates:

    def test_sanction_none(self):
        node = factories.NodeFactory()
        assert bool(node.sanction) is False

    def test_sanction_embargo_termination_first(self):
        embargo_termination_approval = factories.EmbargoTerminationApprovalFactory()
        registration = Registration.find_one(Q('embargo_termination_approval', 'eq', embargo_termination_approval))
        assert registration.sanction == embargo_termination_approval

    def test_sanction_retraction(self):
        retraction = factories.RetractionFactory()
        registration = Registration.find_one(Q('retraction', 'eq', retraction))
        assert registration.sanction == retraction

    def test_sanction_embargo(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.find_one(Q('embargo', 'eq', embargo))
        assert registration.sanction == embargo

    def test_sanction_registration_approval(self):
        registration_approval = factories.RegistrationApprovalFactory()
        registration = Registration.find_one(Q('registration_approval', 'eq', registration_approval))
        assert registration.sanction == registration_approval

    def test_sanction_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node) as registration:
            approval = registration.registration_approval
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.sanction == approval

    def test_is_pending_registration(self):
        registration_approval = factories.RegistrationApprovalFactory()
        registration = Registration.find_one(Q('registration_approval', 'eq', registration_approval))
        assert registration_approval.is_pending_approval
        assert registration.is_pending_registration

    def test_is_pending_registration_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_pending_registration

    def test_is_registration_approved(self):
        registration_approval = factories.RegistrationApprovalFactory(state=Sanction.APPROVED, approve=True)
        registration = Registration.find_one(Q('registration_approval', 'eq', registration_approval))
        assert registration.is_registration_approved

    def test_is_registration_approved_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node) as registration:
            registration.registration_approval.state = Sanction.APPROVED
            registration.registration_approval.save()
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_registration_approved is True

    def test_is_retracted(self):
        retraction = factories.RetractionFactory(state=Sanction.APPROVED, approve=True)
        registration = Registration.find_one(Q('retraction', 'eq', retraction))
        assert registration.is_retracted

    @mock.patch('osf.models.node.AbstractNode.update_search')
    def test_is_retracted_searches_parents(self, mock_update_search):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, autoapprove=True, retraction=True, autoapprove_retraction=True) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_retracted is True

    def test_is_pending_retraction(self):
        retraction = factories.RetractionFactory()
        registration = Registration.find_one(Q('retraction', 'eq', retraction))
        assert retraction.is_pending_approval is True
        assert registration.is_pending_retraction is True

    @mock.patch('osf.models.node.AbstractNode.update_search')
    def test_is_pending_retraction_searches_parents(self, mock_update_search):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, autoapprove=True, retraction=True) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_pending_retraction is True

    def test_embargo_end_date(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.find_one(Q('embargo', 'eq', embargo))
        assert registration.embargo_end_date == embargo.embargo_end_date

    def test_embargo_end_date_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, embargo=True) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.embargo_end_date == registration.embargo_end_date

    def test_is_pending_embargo(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.find_one(Q('embargo', 'eq', embargo))
        assert embargo.is_pending_approval
        assert registration.is_pending_embargo

    def test_is_pending_embargo_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, embargo=True) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_pending_embargo

    def test_is_embargoed(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.find_one(Q('embargo', 'eq', embargo))
        registration.embargo.state = Sanction.APPROVED
        registration.embargo.save()
        assert registration.is_embargoed

    def test_is_embargoed_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, embargo=True, autoapprove=True) as registration:
            sub_reg = registration._nodes.first()._nodes.first()
            assert sub_reg.is_embargoed


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
        schema = MetaSchema.find(
            Q('schema_version', 'eq', 2)
        )[0]
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
        draft = factories.DraftRegistrationFactory(branched_from=project)
        draft2 = factories.DraftRegistrationFactory(branched_from=project, registered_node=deleted_registration)
        finished_draft = factories.DraftRegistrationFactory(branched_from=project, registered_node=registration)
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
