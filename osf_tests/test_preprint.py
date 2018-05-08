import urlparse
import datetime

import pytest
from website import settings
from framework.auth.core import Auth

from osf_tests.factories import (
    ProjectFactory,
    UserFactory,
    PreprintFactory,
    NodeFactory,
    SubjectFactory
)

pytestmark = pytest.mark.django_db

@pytest.fixture()
def user():
    return UserFactory()

@pytest.fixture()
def node(user):
    return NodeFactory(creator=user)

@pytest.fixture()
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def preprint(user):
    return PreprintFactory(creator=user)

@pytest.fixture()
def auth(user):
    return Auth(user)

@pytest.fixture()
def subject():
    return SubjectFactory()


class TestPreprintFactory:
    def test_preprint_factory(self, preprint):
        assert preprint.title is not None
        assert preprint.description is not None
        assert preprint.provider is not None
        assert preprint.node is not None
        assert preprint.is_published is True
        assert preprint.is_public is True
        assert preprint.creator is not None
        assert preprint.files.first() == preprint.primary_file
        assert preprint.deleted is None
        assert preprint.root_folder is not None

class TestPreprintProperties:
    def test_contributors(self, preprint):
        assert len(preprint.contributors) == 1
        assert preprint.contributors[0] == preprint.creator

    def test_verified_publishable(self, preprint):
        preprint.is_published = False
        assert preprint.verified_publishable is False

        preprint.is_published = True
        preprint.deleted = datetime.datetime.now()
        assert preprint.verified_publishable is False

        preprint.deleted = None
        assert preprint.verified_publishable is True

    def test_preprint_doi(self, preprint):
        assert preprint.preprint_doi == '{}osf.io/{}'.format(settings.DOI_NAMESPACE.replace('doi:', ''), preprint._id)

    def test_is_preprint_orphan(self, preprint):
        assert preprint.is_preprint_orphan is False
        preprint.primary_file = None
        assert preprint.is_preprint_orphan is True

    def test__has_abandoned_preprint(self, preprint):
        assert preprint._has_abandoned_preprint is False
        preprint.is_published = False
        assert preprint._has_abandoned_preprint is True

    def test_has_submitted_preprint(self, preprint):
        assert preprint.has_submitted_preprint is False
        preprint.machine_state = 'initial'
        assert preprint.has_submitted_preprint is True

    def test_deep_url(self, preprint):
        assert preprint.deep_url == '/preprints/{}/'.format(preprint._id)

    def test_url_url(self, preprint):
        assert preprint.url == '/preprints/{}/{}/'.format(preprint.provider._id, preprint._id)

    def test_absolute_url(self, preprint):
        assert preprint.absolute_url == urlparse.urljoin(
            preprint.provider.domain if preprint.provider.domain_redirect_enabled else settings.DOMAIN,
            preprint.url
        )

    def test_absolute_api_v2_url(self, preprint):
        assert '/preprints/{}/'.format(preprint._id) in preprint.absolute_api_v2_url

    def test_visible_contributor_ids(self, preprint):
        assert preprint.visible_contributor_ids[0] == preprint.creator._id

    def test_all_tags(self, preprint, auth):
        preprint.add_tags(['test_tag_1'], auth)
        preprint.save()

        assert len(preprint.all_tags) == 1
        assert preprint.all_tags[0].name == 'test_tag_1'

    def test_system_tags(self, preprint):
        assert preprint.system_tags.exists() is False
