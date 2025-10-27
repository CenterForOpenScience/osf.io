import pytest
from faker import Faker
from osf_tests.factories import PreprintFactory, AuthUserFactory, PreprintProviderFactory
from osf.models import Preprint
from framework.auth import Auth

fake = Faker()


@pytest.fixture()
def creator():
    return AuthUserFactory()


@pytest.fixture()
def auth(creator):
    return Auth(user=creator)


@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory()


@pytest.fixture
def factory_preprint():
    return PreprintFactory()


@pytest.fixture
def model_preprint(creator, preprint_provider):
    return Preprint.create(
        creator=creator,
        provider=preprint_provider,
        title='Preprint',
        description='Abstract'
    )


@pytest.mark.django_db
class TestPreprintFactory:
    def test_factory_creates_valid_instance(self):
        preprint = PreprintFactory()
        assert preprint.title is not None
        assert preprint.description is not None
        assert preprint.creator is not None
        assert preprint.provider is not None

    def test_factory_build_method(self):
        preprint = PreprintFactory._build(Preprint)
        assert isinstance(preprint, Preprint)
        assert preprint.pk is None

    def test_factory_create_method(self):
        preprint = PreprintFactory()
        assert isinstance(preprint, Preprint)
        assert preprint.pk is not None

    def test_factory_custom_fields(self):
        custom_title = 'Custom Preprint Title'
        custom_description = 'Custom Description'
        preprint = PreprintFactory(title=custom_title, description=custom_description)
        assert preprint.title == custom_title
        assert preprint.description == custom_description

    def test_factory_affiliated_institutions(self):
        preprint = PreprintFactory()
        assert preprint.affiliated_institutions.count() == 0

    def test_factory_published_state(self):
        preprint = PreprintFactory(is_published=True)
        assert preprint.is_published
        assert preprint.date_published is not None

    def test_factory_unpublished_state(self):
        preprint = PreprintFactory(is_published=False)
        assert not preprint.is_published
        assert preprint.date_published is None

    def test_factory_creates_guid_and_version(self):
        preprint = PreprintFactory()
        guid = preprint.guids.first()
        guid_version = guid.versions.first()

        assert guid is not None
        assert guid.referent == preprint

        assert guid_version is not None
        assert guid_version.referent == preprint
        assert guid_version.guid == guid
        assert guid_version.version == 1

    def test_create_version_increments_version_number(self):
        original_preprint = PreprintFactory()
        original_guid = original_preprint.guids.first()
        assert original_guid is not None
        assert original_guid.versions.count() == 1

        new_preprint = PreprintFactory.create_version(create_from=original_preprint)
        assert new_preprint is not None
        assert original_guid.versions.count() == 2

        versions = original_guid.versions.order_by('version')
        assert versions[0].version == 1  # Original version
        assert versions[1].version == 2  # New version

    def test_create_version_copies_fields(self):
        title = 'Original Preprint Title'
        description = 'Original description.'
        original_preprint = PreprintFactory(title=title, description=description)

        new_preprint = PreprintFactory.create_version(create_from=original_preprint)

        assert new_preprint.title == title
        assert new_preprint.description == description
        assert new_preprint.provider == original_preprint.provider
        assert new_preprint.creator == original_preprint.creator

    def test_create_version_copies_subjects(self):
        original_preprint = PreprintFactory()
        original_subjects = [[subject._id] for subject in original_preprint.subjects.all()]

        new_preprint = PreprintFactory.create_version(create_from=original_preprint)

        new_subjects = [[subject._id] for subject in new_preprint.subjects.all()]
        assert original_subjects == new_subjects

    def test_create_version_copies_contributors(self):
        original_preprint = PreprintFactory()
        contributors_before = list(
            original_preprint.contributor_set.exclude(user=original_preprint.creator).values_list('user_id', flat=True)
        )

        new_preprint = PreprintFactory.create_version(create_from=original_preprint)

        contributors_after = list(
            new_preprint.contributor_set.exclude(user=new_preprint.creator).values_list('user_id', flat=True)
        )
        assert contributors_before == contributors_after

    def test_create_version_with_machine_state(self):
        original_preprint = PreprintFactory()
        new_preprint = PreprintFactory.create_version(
            create_from=original_preprint, final_machine_state='accepted'
        )

        assert new_preprint.machine_state == 'accepted'

    def test_create_version_published_flag(self):
        original_preprint = PreprintFactory(is_published=True)
        original_guid = original_preprint.guids.first()
        new_preprint = PreprintFactory.create_version(
            create_from=original_preprint, is_published=True
        )
        original_guid.refresh_from_db()
        assert new_preprint.is_published is True
        assert original_guid.referent == new_preprint

    def test_create_version_unpublished(self):
        original_preprint = PreprintFactory(is_published=True)
        new_preprint = PreprintFactory.create_version(
            create_from=original_preprint, is_published=False, set_doi=False, final_machine_state='pending'
        )
        assert new_preprint.is_published is False
        assert new_preprint.machine_state == 'pending'
