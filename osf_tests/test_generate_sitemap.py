import os

import pytest
import mock
import shutil
import tempfile
import xml
from future.moves.urllib.parse import urljoin

from scripts import generate_sitemap
from osf_tests.factories import (AuthUserFactory, ProjectFactory, RegistrationFactory, CollectionFactory,
                                 PreprintFactory, PreprintProviderFactory, EmbargoFactory, UnconfirmedUserFactory)
from website import settings


def get_all_sitemap_urls():
    # Create temporary directory for the sitemaps to be generated

    generate_sitemap.main()

    # Parse the generated XML sitemap file
    with open(os.path.join(settings.STATIC_FOLDER, 'sitemaps/sitemap_0.xml')) as f:
        tree = xml.etree.ElementTree.parse(f)

    shutil.rmtree(settings.STATIC_FOLDER)

    # Get all the urls in the sitemap
    # Note: namespace was defined in the XML file, therefore necessary to include in tag
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
    urls = [element.text for element in tree.iter(namespace + 'loc')]

    return urls


@pytest.mark.django_db
class TestGenerateSitemap:

    @pytest.fixture(autouse=True)
    def user_admin_project_public(self):
        return AuthUserFactory()

    @pytest.fixture(autouse=True)
    def user_unconfirmed(self):
        return UnconfirmedUserFactory()

    @pytest.fixture(autouse=True)
    def user_admin_project_private(self):
        return AuthUserFactory()

    @pytest.fixture(autouse=True)
    def project_registration_public(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def project_preprint_osf(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def project_preprint_other(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def project_private(self, user_admin_project_private):
        return ProjectFactory(creator=user_admin_project_private, is_public=False)

    @pytest.fixture(autouse=True)
    def project_deleted(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_deleted=True)

    @pytest.fixture(autouse=True)
    def registration_active(self, user_admin_project_public, project_registration_public):
        return RegistrationFactory(project=project_registration_public,
                                             creator=user_admin_project_public,
                                             is_public=True)

    @pytest.fixture(autouse=True)
    def registration_embargoed(self, user_admin_project_public, project_registration_public):
        return RegistrationFactory(project=project_registration_public,
                                             creator=user_admin_project_public,
                                             embargo=EmbargoFactory(user=user_admin_project_public))

    @pytest.fixture(autouse=True)
    def collection(self, user_admin_project_public):
        return CollectionFactory(creator=user_admin_project_public)

    @pytest.fixture(autouse=True)
    def provider_osf(self):
        # Note: at least a provider whose _id == 'osf' have to exist for the script to work
        return PreprintProviderFactory(_id='osf', name='osfprovider')

    @pytest.fixture(autouse=True)
    def provider_other(self):
        return PreprintProviderFactory(_id='adl', name='anotherprovider')

    @pytest.fixture(autouse=True)
    def preprint_osf(self, project_preprint_osf, user_admin_project_public, provider_osf):
        return PreprintFactory(project=project_preprint_osf,
                                             creator=user_admin_project_public,
                                             provider=provider_osf)

    @pytest.fixture(autouse=True)
    def preprint_other(self, project_preprint_other, user_admin_project_public, provider_other):
        return PreprintFactory(project=project_preprint_other,
                                             creator=user_admin_project_public,
                                             provider=provider_other)

    @pytest.fixture(autouse=True)
    def all_included_links(self, user_admin_project_public, user_admin_project_private, project_registration_public,
                             project_preprint_osf, project_preprint_other,
                             registration_active, provider_other, preprint_osf,
                             preprint_other):
        # Return urls of all fixtures
        urls_to_include = [item['loc'] for item in settings.SITEMAP_STATIC_URLS]
        urls_to_include.extend([
            user_admin_project_public.url,
            user_admin_project_private.url,
            project_registration_public.url,
            project_preprint_osf.url,
            project_preprint_other.url,
            registration_active.url,
            '/preprints/{}/'.format(preprint_osf._id),
            '/preprints/{}/{}/'.format(provider_other._id, preprint_other._id),
            '/{}/download/?format=pdf'.format(preprint_osf._id),
            '/{}/download/?format=pdf'.format(preprint_other._id)
        ])
        urls_to_include = [urljoin(settings.DOMAIN, item) for item in urls_to_include]

        return urls_to_include

    @pytest.fixture()
    def create_tmp_directory(self):
        return tempfile.mkdtemp()

    def test_all_links_included(self, all_included_links, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        urls_to_include = all_included_links

        assert len(urls_to_include) == len(urls)
        assert set(urls_to_include) == set(urls)

    def test_unconfirmed_user_not_included(self, create_tmp_directory, user_unconfirmed):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urljoin(settings.DOMAIN, user_unconfirmed.url) not in urls

    def test_collection_link_not_included(self, collection, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urljoin(settings.DOMAIN, collection.url) not in urls

    def test_private_project_link_not_included(self, project_private, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urljoin(settings.DOMAIN, project_private.url) not in urls

    def test_embargoed_registration_link_not_included(self, registration_embargoed, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urljoin(settings.DOMAIN, registration_embargoed.url) not in urls

    def test_deleted_project_link_not_included(self, project_deleted, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urljoin(settings.DOMAIN, project_deleted.url) not in urls
