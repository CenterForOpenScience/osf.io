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
