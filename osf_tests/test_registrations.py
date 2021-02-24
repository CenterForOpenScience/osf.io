import mock
import pytest

from addons.wiki.models import WikiVersion
from django.core.exceptions import ValidationError
from django.utils import timezone
from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from nose.tools import assert_raises
from osf.models import Node, Registration, Sanction, RegistrationSchema, NodeLog
from addons.wiki.models import WikiPage
from osf.utils.permissions import ADMIN

from website import settings

from . import factories
from .utils import assert_datetime_equal, mock_archive
from .factories import get_default_metaschema, DraftRegistrationFactory
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.providers.workflows import Workflows
from osf.migrations import update_provider_auth_groups
from osf.models.action import RegistrationAction
from osf_tests.management_commands.test_migration_registration_responses import (
    prereg_registration_responses,
    prereg_registration_metadata_built,
    veer_registration_responses,
    veer_condensed
)
from osf.utils.workflows import (
    RegistrationModerationStates,
    RegistrationModerationTriggers,
    SanctionStates
)

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

    data = {'some': 'data'}
    draft_reg = DraftRegistrationFactory(registration_metadata=data, branched_from=project)
    registration2 = factories.RegistrationFactory(
        project=project,
        user=user2,
        draft_registration=draft_reg,
    )
    assert registration2.registered_from == project
    assert registration2.registered_user == user2
    assert (
        registration2.registered_meta[get_default_metaschema()._id] ==
        data
    )


class TestRegistration:

    def test_registered_schema_id(self):
        reg = factories.RegistrationFactory()
        assert reg.registered_schema_id == reg.registered_schema.get()._id

    # Regression test for https://openscience.atlassian.net/browse/PLAT-776
    # Some very old registrations on prod don't have a schema
    def test_registered_schema_id_with_no_schema(self):
        reg = factories.RegistrationFactory()
        reg.registered_schema.clear()
        assert reg.registered_schema_id is None

    def test_update_category(self, auth):
        reg = factories.RegistrationFactory(category='instrumentation')
        new_category = 'software'
        reg.update({'category': new_category}, auth=auth)
        assert reg.category == new_category

        last_log = reg.logs.latest()
        assert last_log.action == NodeLog.CATEGORY_UPDATED
        assert last_log.params['category_new'] == new_category
        assert last_log.params['category_original'] == 'instrumentation'

    def test_update_article_doi(self, auth):
        reg = factories.RegistrationFactory()
        reg.article_doi = '10.1234/giraffe'
        reg.save()
        new_article_doi = '10.12345/elephant'
        reg.update({'article_doi': new_article_doi}, auth=auth)
        assert reg.article_doi == new_article_doi

        last_log = reg.logs.latest()
        assert last_log.action == NodeLog.ARTICLE_DOI_UPDATED
        assert last_log.params['article_doi_new'] == new_article_doi
        assert last_log.params['article_doi_original'] == '10.1234/giraffe'


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
        project_second_log = project.logs.all()[:2][1]
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
        project.add_contributor(user2, permissions=ADMIN)
        shared_component.add_contributor(user2, permissions=ADMIN)
        shared_subproject.add_contributor(user2, permissions=ADMIN)

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
        # allowance increased in OSF-9050, if this fails sporadically again then registrations may need to be optimized or this test reworked
        assert_datetime_equal(registration.registered_date, timezone.now(), allowance=10000)

    def test_registered_addons(self, registration):
        assert (
            [addon.config.short_name for addon in registration.get_addons()] ==
            [addon.config.short_name for addon in registration.registered_from.get_addons()]
        )

    def test_registered_user(self, project):
        # Add a second contributor
        user2 = factories.UserFactory()
        project.add_contributor(user2, permissions=ADMIN)
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
        assert WikiPage.objects.get_wiki_pages_latest(registration).exists() is False
        assert registration.wikis.all().exists() is False
        assert registration.wiki_private_uuids == {}

    @mock.patch('website.project.signals.after_create_registration')
    def test_registration_clones_project_wiki_pages(self, mock_signal, project, user):
        project = factories.ProjectFactory(creator=user, is_public=True)
        wiki_page = WikiFactory(
            user=user,
            node=project,
        )
        wiki = WikiVersionFactory(
            wiki_page=wiki_page,
        )
        current_wiki = WikiVersionFactory(
            wiki_page=wiki_page,
            identifier=2
        )
        draft_reg = factories.DraftRegistrationFactory(branched_from=project)
        registration = project.register_node(get_default_metaschema(), Auth(user), draft_reg, None)
        assert registration.wiki_private_uuids == {}

        registration_wiki_current = WikiVersion.objects.get_for_node(registration, current_wiki.wiki_page.page_name)
        assert registration_wiki_current.wiki_page.node == registration
        assert registration_wiki_current._id != current_wiki._id
        assert registration_wiki_current.identifier == 2

        registration_wiki_version = WikiVersion.objects.get_for_node(registration, wiki.wiki_page.page_name, version=1)
        assert registration_wiki_version.wiki_page.node == registration
        assert registration_wiki_version._id != wiki._id
        assert registration_wiki_version.identifier == 1

    def test_legacy_private_registrations_can_be_made_public(self, registration, auth):
        registration.is_public = False
        registration.set_privacy(Node.PUBLIC, auth=auth)
        assert registration.is_public


class TestRegisterNodeContributors:

    @pytest.fixture()
    def project_two(self, user, auth):
        return factories.ProjectFactory(creator=user)

    @pytest.fixture()
    def component(self, user, auth, project_two):
        return factories.NodeFactory(
            creator=user,
            parent=project_two,
        )

    @pytest.fixture()
    def contributor_unregistered(self, user, auth, project_two):
        ret = project_two.add_unregistered_contributor(fullname='Johnny Git Gud', email='ford.prefect@hitchhikers.com', auth=auth)
        project_two.save()
        return ret

    @pytest.fixture()
    def contributor_unregistered_no_email(self, user, auth, project_two, component):
        ret = component.add_unregistered_contributor(fullname='Johnny B. Bard', email='', auth=auth)
        component.save()
        return ret

    @pytest.fixture()
    def registration(self, project_two, component, contributor_unregistered, contributor_unregistered_no_email):
        with mock_archive(project_two, autoapprove=True) as registration:
            return registration

    def test_unregistered_contributors_unclaimed_records_get_copied(self, user, project, component, registration, contributor_unregistered, contributor_unregistered_no_email):
        contributor_unregistered.refresh_from_db()
        contributor_unregistered_no_email.refresh_from_db()
        assert registration.contributors.filter(id=contributor_unregistered.id).exists()
        assert registration._id in contributor_unregistered.unclaimed_records

        # component
        component_registration = registration.nodes[0]
        assert component_registration.contributors.filter(id=contributor_unregistered_no_email.id).exists()
        assert component_registration._id in contributor_unregistered_no_email.unclaimed_records


# copied from tests/test_registrations
class TestNodeSanctionStates:

    def test_sanction_none(self):
        node = factories.NodeFactory()
        assert bool(node.sanction) is False

    def test_sanction_embargo_termination_first(self):
        embargo_termination_approval = factories.EmbargoTerminationApprovalFactory()
        registration = Registration.objects.get(embargo_termination_approval=embargo_termination_approval)
        assert registration.sanction == embargo_termination_approval

    def test_sanction_retraction(self):
        retraction = factories.RetractionFactory()
        registration = Registration.objects.get(retraction=retraction)
        assert registration.sanction == retraction

    def test_sanction_embargo(self):
        embargo = factories.EmbargoFactory()
        registration = Registration.objects.get(embargo=embargo)
        assert registration.sanction == embargo

    def test_sanction_registration_approval(self):
        registration_approval = factories.RegistrationApprovalFactory()
        registration = Registration.objects.get(registration_approval=registration_approval)
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
        registration = Registration.objects.get(registration_approval=registration_approval)
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
        registration = Registration.objects.get(registration_approval=registration_approval)
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
        registration = Registration.objects.get(retraction=retraction)
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
        registration = Registration.objects.get(retraction=retraction)
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
        registration = Registration.objects.get(embargo=embargo)
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
        registration = Registration.objects.get(embargo=embargo)
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
        registration = Registration.objects.get(embargo=embargo)
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


@pytest.mark.enable_implicit_clean
class TestDOIValidation:

    def test_validate_bad_doi(self):
        reg = factories.RegistrationFactory()

        with pytest.raises(ValidationError):
            reg.article_doi = 'nope'
            reg.save()
        with pytest.raises(ValidationError):
            reg.article_doi = 'https://dx.doi.org/10.123.456'
            reg.save()  # should save the bare DOI, not a URL
        with pytest.raises(ValidationError):
            reg.article_doi = 'doi:10.10.1038/nwooo1170'
            reg.save()  # should save without doi: prefix

    def test_validate_good_doi(self):
        reg = factories.RegistrationFactory()

        doi = '10.11038/nwooo1170'
        reg.article_doi = doi
        reg.save()
        assert reg.article_doi == doi


class TestRegistrationMixin:
    @pytest.fixture()
    def draft_prereg(self, prereg_schema):
        return factories.DraftRegistrationFactory(
            registration_schema=prereg_schema,
            registration_metadata={},
        )

    @pytest.fixture()
    def draft_veer(self, veer_schema):
        return factories.DraftRegistrationFactory(
            registration_schema=veer_schema,
            registration_metadata={},
        )

    @pytest.fixture()
    def prereg_schema(self):
        return RegistrationSchema.objects.get(
            name='Prereg Challenge',
            schema_version=2
        )

    @pytest.fixture()
    def veer_schema(self):
        return RegistrationSchema.objects.get(
            name__icontains='Pre-Registration in Social Psychology',
            schema_version=2
        )

    def test_expand_registration_responses(self, draft_prereg):
        draft_prereg.registration_responses = prereg_registration_responses
        draft_prereg.save()
        assert draft_prereg.registration_metadata == {}

        registration_metadata = draft_prereg.expand_registration_responses()

        assert registration_metadata == prereg_registration_metadata_built

    def test_expand_registration_responses_veer(self, draft_veer):
        draft_veer.registration_responses = veer_registration_responses
        draft_veer.save()
        assert draft_veer.registration_metadata == {}

        registration_metadata = draft_veer.expand_registration_responses()

        assert registration_metadata == veer_condensed


class TestRegistationModerationStates():

    @pytest.fixture
    def embargo(self):
        return factories.EmbargoFactory()

    @pytest.fixture
    def registration_approval(self):
        return factories.RegistrationApprovalFactory()

    @pytest.fixture
    def retraction(self):
        return factories.RetractionFactory()

    @pytest.fixture
    def embargo_termination(self):
        return factories.EmbargoTerminationApprovalFactory()

    @pytest.fixture
    def moderator(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def provider(self, moderator):
        provider = factories.RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def moderated_registration(self, provider):
        return factories.RegistrationFactory(provider=provider, is_public=True)

    @pytest.fixture
    def withdraw_action(self, moderated_registration):
        action = RegistrationAction.objects.create(
            creator=moderated_registration.creator,
            target=moderated_registration,
            trigger=RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name,
            from_state=RegistrationModerationStates.ACCEPTED.db_name,
            to_state=RegistrationModerationStates.PENDING_WITHDRAW.db_name,
            comment='yo'
        )
        action.save()
        return action

    @pytest.fixture
    def withdraw_action_for_retraction(self, retraction):
        action = RegistrationAction.objects.create(
            creator=retraction.target_registration.creator,
            target=retraction.target_registration,
            trigger=RegistrationModerationTriggers.REQUEST_WITHDRAWAL.db_name,
            from_state=RegistrationModerationStates.ACCEPTED.db_name,
            to_state=RegistrationModerationStates.PENDING_WITHDRAW.db_name,
            comment='yo'
        )
        action.save()
        return action

    def test_embargo_states(self, embargo):
        registration = embargo.target_registration
        embargo.to_UNAPPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.INITIAL.db_name

        embargo.to_PENDING_MODERATION()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        embargo.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        embargo.to_COMPLETED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        embargo.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.REJECTED.db_name

        embargo.to_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.REVERTED.db_name

    def test_registration_approval_states(self, registration_approval):
        registration = registration_approval.target_registration
        registration_approval.to_UNAPPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.INITIAL.db_name

        registration_approval.to_PENDING_MODERATION()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING.db_name

        registration_approval.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        registration_approval.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.REJECTED.db_name

        registration_approval.to_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.REVERTED.db_name

    def test_retraction_states_over_registration_approval(self, registration_approval, withdraw_action):
        registration = registration_approval.target_registration
        registration.is_public = True
        retraction = registration.retract_registration(registration.creator, justification='test')
        registration_approval.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW_REQUEST.db_name

        retraction.to_PENDING_MODERATION()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW.db_name

        retraction.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

        retraction.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        retraction.to_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    def test_retraction_states_over_embargo(self, embargo):
        registration = embargo.target_registration
        retraction = registration.retract_registration(user=registration.creator, justification='test')
        embargo.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW_REQUEST.db_name

        retraction.to_PENDING_MODERATION()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW.db_name

        retraction.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

        retraction.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        retraction.to_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        embargo.to_COMPLETED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        retraction.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    def test_embargo_termination_states(self, embargo_termination):
        registration = embargo_termination.target_registration
        assert registration.moderation_state == RegistrationModerationStates.PENDING_EMBARGO_TERMINATION.db_name

        embargo_termination.to_REJECTED()
        registration.update_moderation_state()
        assert registration.moderation_state == RegistrationModerationStates.EMBARGO.db_name

        embargo_termination.to_APPROVED()
        registration.update_moderation_state()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

    def test_retraction_states_over_embargo_termination(self, embargo_termination):
        registration = embargo_termination.target_registration
        embargo_termination.accept()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        retraction = registration.retract_registration(user=registration.creator, justification='because')
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW_REQUEST.db_name

        retraction.to_PENDING_MODERATION()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.PENDING_WITHDRAW.db_name

        retraction.to_APPROVED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

        retraction.to_MODERATOR_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name

        retraction.to_REJECTED()
        registration.refresh_from_db()
        assert registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name


class TestForcedWithdrawal():

    @pytest.fixture
    def embargo_termination(self):
        return factories.EmbargoTerminationApprovalFactory()

    @pytest.fixture
    def moderator(self):
        return factories.AuthUserFactory()

    @pytest.fixture
    def provider(self, moderator):
        provider = factories.RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.get_group('moderator').user_set.add(moderator)
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def moderated_registration(self, provider):
        registration = factories.RegistrationFactory(provider=provider, is_public=True)
        # Move to implicit ACCEPTED state
        registration.update_moderation_state()
        return registration

    @pytest.fixture
    def unmoderated_registration(self):
        registration = factories.RegistrationFactory(is_public=True)
        # Move to implicit ACCEPTED state
        registration.update_moderation_state()
        return registration

    def test_force_retraction_changes_state(self, moderated_registration, moderator):
        moderated_registration.retract_registration(
            user=moderator, justification='because', moderator_initiated=True)

        moderated_registration.refresh_from_db()
        assert moderated_registration.is_retracted
        assert moderated_registration.retraction.approval_stage is SanctionStates.APPROVED
        assert moderated_registration.moderation_state == RegistrationModerationStates.WITHDRAWN.db_name

    def test_force_retraction_writes_action(self, moderated_registration, moderator):
        justification = 'because power'
        moderated_registration.retract_registration(
            user=moderator, justification=justification, moderator_initiated=True)

        expected_justification = 'Force withdrawn by moderator: ' + justification
        assert moderated_registration.retraction.justification == expected_justification

        action = RegistrationAction.objects.last()
        assert action.trigger == RegistrationModerationTriggers.FORCE_WITHDRAW.db_name
        assert action.comment == expected_justification
        assert action.from_state == RegistrationModerationStates.ACCEPTED.db_name
        assert action.to_state == RegistrationModerationStates.WITHDRAWN.db_name

    def test_cannot_force_retraction_on_unmoderated_registration(self):
        unmoderated_registration = factories.RegistrationFactory(is_public=True)
        with assert_raises(ValueError):
            unmoderated_registration.retract_registration(
                user=unmoderated_registration.creator, justification='', moderator_initiated=True)

    def test_nonmoderator_cannot_force_retraction(self, moderated_registration):
        with assert_raises(PermissionsError):
            moderated_registration.retract_registration(
                user=moderated_registration.creator, justification='', moderator_initiated=True)

        assert moderated_registration.retraction is None
        assert moderated_registration.moderation_state == RegistrationModerationStates.ACCEPTED.db_name
