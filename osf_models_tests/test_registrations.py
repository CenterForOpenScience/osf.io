import mock
import pytest

from django.utils import timezone
from framework.auth.core import Auth
from osf_models.models import Node, Registration, Sanction
from osf_models.modm_compat import Q

from website import settings
from website.project.model import ensure_schemas
from website.util.permissions import READ, WRITE, ADMIN

from . import factories
from .utils import assert_datetime_equal, mock_archive
from .factories import get_default_metaschema


@pytest.fixture(autouse=True)
def _ensure_schemas():
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
@pytest.mark.django_db
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
@pytest.mark.django_db
class TestRegisterNode:

    # def setUp(self):
    #     super(TestRegisterNode, self).setUp()
    #     ensure_schemas()
    #     self.user = factories.UserFactory()
    #     self.auth = Auth(user=self.user)
    #     self.project = ProjectFactory(creator=self.user)
    #     self.link = PrivateLinkFactory()
    #     self.link.nodes.append(self.project)
    #     self.link.save()
    #     self.registration = RegistrationFactory(project=self.project)

    @pytest.fixture()
    def registration(self, project):
        reg = factories.RegistrationFactory(project=project)
        private_link = factories.PrivateLinkFactory()
        private_link.nodes.add(reg)
        private_link.save()
        return reg

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

    @pytest.mark.skip('fork_node not yet implemented')
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
        assert registration.nodes.count() == 2
        # TODO: Test ordering when node ordering is implemented
        assert(
            set(registration.nodes.values_list('title', flat=True)) ==
            set(project.nodes.values_list('title', flat=True))
        )
        # Nodes are copies and not the original versions
        for node in registration.nodes.all():
            assert node not in project.nodes.all()
            assert node.is_registration

    def test_private_contributor_registration(self, project, user):

        # Create some nodes
        # component
        factories.NodeFactory(
            creator=user,
            parent=project,
        )
        # subproject
        factories.ProjectFactory(
            creator=user,
            parent=project,
        )

        # Create some nodes to share
        shared_component = factories.NodeFactory(
            creator=user,
            parent=project,
        )
        shared_subproject = factories.ProjectFactory(
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
        for registered_node in registration.nodes.all():
            assert registered_node.root == registration
            assert registered_node.registered_from
            assert registered_node.parent_node == registration
            assert registered_node.registered_from.parent_node == project

    def test_is_registration(self, registration):
        assert registration.is_registration

    def test_registered_date(self, registration):
        assert_datetime_equal(registration.registered_date, timezone.now(), allowance=3000)

    @pytest.mark.skip('addons not yet implemented')
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

        node.add_affiliated_intitution(institution, user=user)
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

    @pytest.mark.skip('NodeWikiPage not yet implemented')
    @mock.patch('website.project.signals.after_create_registration')
    def test_registration_clones_project_wiki_pages(self, mock_signal):
        project = factories.ProjectFactory(creator=self.user, is_public=True)
        wiki = factories.NodeWikiFactory(node=project)
        current_wiki = factories.NodeWikiFactory(node=project, version=2)
        registration = project.register_node(get_default_metaschema(), Auth(self.user), '', None)
        assert_equal(self.registration.wiki_private_uuids, {})

        registration_wiki_current = NodeWikiPage.load(registration.wiki_pages_current[current_wiki.page_name])
        assert_equal(registration_wiki_current.node, registration)
        assert_not_equal(registration_wiki_current._id, current_wiki._id)

        registration_wiki_version = NodeWikiPage.load(registration.wiki_pages_versions[wiki.page_name][0])
        assert_equal(registration_wiki_version.node, registration)
        assert_not_equal(registration_wiki_version._id, wiki._id)

    def test_legacy_private_registrations_can_be_made_public(self, registration, auth):
        registration.is_public = False
        registration.set_privacy(Node.PUBLIC, auth=auth)
        assert registration.is_public


# copied from tests/test_registrations
@pytest.mark.django_db
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
            sub_reg = registration.nodes.first().nodes.first()
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
            sub_reg = registration.nodes.first().nodes.first()
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
            sub_reg = registration.nodes.first().nodes.first()
            assert sub_reg.is_registration_approved is True

    def test_is_retracted(self):
        retraction = factories.RetractionFactory(state=Sanction.APPROVED, approve=True)
        registration = Registration.find_one(Q('retraction', 'eq', retraction))
        assert registration.is_retracted

    def test_is_retracted_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, autoapprove=True, retraction=True, autoapprove_retraction=True) as registration:
            sub_reg = registration.nodes[0].nodes[0]
            assert sub_reg.is_retracted is True

    def test_is_pending_retraction(self):
        retraction = factories.RetractionFactory()
        registration = Registration.find_one(Q('retraction', 'eq', retraction))
        assert retraction.is_pending_approval is True
        assert registration.is_pending_retraction is True

    def test_is_pending_retraction_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, autoapprove=True, retraction=True) as registration:
            sub_reg = registration.nodes.first().nodes.first()
            assert sub_reg.is_pending_retraction is True

    def test_embargo_end_date(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.find_one(Q('embargo', 'eq', embargo))
        assert registration.embargo_end_date == embargo.end_date

    def test_embargo_end_date_searches_parents(self):
        user = factories.UserFactory()
        node = factories.ProjectFactory(creator=user)
        child = factories.NodeFactory(creator=user, parent=node)
        factories.NodeFactory(creator=user, parent=child)
        with mock_archive(node, embargo=True) as registration:
            sub_reg = registration.nodes.first().nodes.first()
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
            sub_reg = registration.nodes.first().nodes.first()
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
            sub_reg = registration.nodes.first().nodes.first()
            assert sub_reg.is_embargoed
