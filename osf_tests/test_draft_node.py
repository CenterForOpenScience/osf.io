import pytest
from framework.auth.core import Auth

from api_tests.utils import disconnected_from_listeners
from osf.models import (
    DraftNode,
    Registration,
    DraftRegistration,
    NodeLicense,
    NodeLog,
)
from osf.exceptions import NodeStateError
from osf.utils.permissions import READ, WRITE, ADMIN
from osf_tests.factories import (
    DraftNodeFactory,
    DraftRegistrationFactory,
    AuthUserFactory,
    SubjectFactory,
    UserFactory,
    InstitutionFactory,
    ProjectFactory,
    get_default_metaschema,
)
from website.project.signals import after_create_registration

pytestmark = pytest.mark.django_db

NEW_YEAR = '2014'
COPYLEFT_HOLDERS = ['Richard Stallman']

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def draft_node(user):
    return DraftNodeFactory(creator=user)

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def draft_registration(user, project):
    return DraftRegistrationFactory(branched_from=project)

@pytest.fixture()
def auth(user):
    return Auth(user)

@pytest.fixture()
def write_contrib():
    return AuthUserFactory()

@pytest.fixture()
def subject():
    return SubjectFactory()

@pytest.fixture()
def institution():
    return InstitutionFactory()

@pytest.fixture()
def title():
    return 'A Study of Elephants'

@pytest.fixture()
def description():
    return 'Loxodonta africana'

@pytest.fixture()
def category():
    return 'Methods and Materials'

@pytest.fixture()
def license():
    return NodeLicense.objects.get(license_id='GPL3')

@pytest.fixture()
def make_complex_draft_registration(title, institution, description, category,
        write_contrib, license, subject, user):
    def make_draft_registration(node=None):
        draft_registration = DraftRegistration.create_from_node(
            user=user,
            schema=get_default_metaschema(),
            data={},
            node=node if node else None
        )
        user.affiliated_institutions.add(institution)
        draft_registration.set_title(title, Auth(user))
        draft_registration.set_description(description, Auth(user))
        draft_registration.category = category
        draft_registration.add_contributor(write_contrib, permissions=WRITE)
        draft_registration.set_node_license(
            {
                'id': license.license_id,
                'year': NEW_YEAR,
                'copyrightHolders': COPYLEFT_HOLDERS
            },
            auth=Auth(user),
            save=True
        )
        draft_registration.add_tag('savanna', Auth(user))
        draft_registration.add_tag('taxonomy', Auth(user))
        draft_registration.set_subjects([[subject._id]], auth=Auth(draft_registration.creator))
        draft_registration.affiliated_institutions.add(institution)
        draft_registration.save()
        return draft_registration
    return make_draft_registration


class TestDraftNode:

    def test_draft_node_creation(self, user):
        draft_node = DraftNode.objects.create(title='Draft Registration', creator_id=user.id)
        assert draft_node.is_public is False
        assert draft_node.has_addon('osfstorage') is True

    def test_create_draft_registration_without_node(self, user):
        data = {'some': 'data'}
        draft = DraftRegistration.create_from_node(
            user=user,
            schema=get_default_metaschema(),
            data=data,
        )
        assert draft.title == 'Untitled'
        assert draft.branched_from.title == 'Untitled'
        assert draft.branched_from.type == 'osf.draftnode'
        assert draft.branched_from.creator == user
        assert len(draft.logs.all()) == 0

    def test_register_draft_node(self, user, draft_node, draft_registration):
        assert draft_node.type == 'osf.draftnode'

        with disconnected_from_listeners(after_create_registration):
            registration = draft_node.register_node(get_default_metaschema(), Auth(user), draft_registration, None)

        assert type(registration) is Registration
        assert draft_node._id != registration._id
        draft_node.reload()
        assert draft_node.type == 'osf.node'
        assert len(draft_node.logs.all()) == 1
        assert draft_node.logs.first().action == NodeLog.PROJECT_CREATED_FROM_DRAFT_REG

    def test_draft_registration_fields_are_copied_back_to_draft_node(self, user, institution,
            subject, write_contrib, title, description, category, license, make_complex_draft_registration):
        draft_registration = make_complex_draft_registration()
        draft_node = draft_registration.branched_from

        with disconnected_from_listeners(after_create_registration):
            draft_registration.register(auth=Auth(user), save=True)

        draft_node.reload()
        assert draft_node.type == 'osf.node'
        assert draft_node.title == title
        assert draft_node.description == description
        assert draft_node.category == category
        assert user in draft_node.contributors.all()
        assert write_contrib in draft_node.contributors.all()

        assert draft_node.get_permissions(user) == [READ, WRITE, ADMIN]
        assert draft_node.get_permissions(write_contrib) == [READ, WRITE]

        assert draft_node.node_license.license_id == license.license_id
        assert draft_node.node_license.name == license.name
        assert draft_node.node_license.copyright_holders == COPYLEFT_HOLDERS

        draft_tags = draft_node.tags.values_list('name', flat=True)
        assert 'savanna' in draft_tags
        assert 'taxonomy' in draft_tags
        assert subject in draft_node.subjects.all()
        assert institution in draft_node.affiliated_institutions.all()

    def test_draft_registration_fields_are_not_copied_back_to_original_node(self, user, institution, project,
            subject, write_contrib, title, description, category, license, make_complex_draft_registration):
        draft_registration = make_complex_draft_registration(node=project)

        with disconnected_from_listeners(after_create_registration):
            draft_registration.register(auth=Auth(user), save=True)

        project.reload()
        assert project.type == 'osf.node'
        assert project.title != title
        assert project.description != description
        assert project.category != category
        assert user in project.contributors.all()
        assert write_contrib not in project.contributors.all()

        assert project.get_permissions(user) == [READ, WRITE, ADMIN]

        assert project.node_license is None
        project_tags = project.tags.values_list('name', flat=True)
        assert 'savanna' not in project_tags
        assert 'taxonomy' not in project_tags
        assert subject not in project.subjects.all()
        assert institution not in project.affiliated_institutions.all()

    def test_cannot_make_draft_node_public(self, draft_node):
        with pytest.raises(NodeStateError):
            draft_node.set_privacy('public', save=True)
