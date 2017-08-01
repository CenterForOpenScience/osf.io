import os

import pytest
import mock
import shutil
import tempfile
import xml
import urlparse

from scripts import generate_sitemap
from osf_tests.factories import (AuthUserFactory, ProjectFactory, RegistrationFactory, CollectionFactory,
                                 PreprintFactory, PreprintProviderFactory, EmbargoFactory)
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
    def user_admin_project_private(self):
        return AuthUserFactory()

    @pytest.fixture(autouse=True)
    def public_project_for_registration(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def project_for_osf_preprint(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def project_for_other_preprint(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_public=True)

    @pytest.fixture(autouse=True)
    def private_project(self, user_admin_project_private):
        return ProjectFactory(creator=user_admin_project_private, is_public=False)

    @pytest.fixture(autouse=True)
    def deleted_project(self, user_admin_project_public):
        return ProjectFactory(creator=user_admin_project_public, is_deleted=True)

    @pytest.fixture(autouse=True)
    def active_registration(self, user_admin_project_public, public_project_for_registration):
        return RegistrationFactory(project=public_project_for_registration,
                                             creator=user_admin_project_public,
                                             is_public=True)

    @pytest.fixture(autouse=True)
    def embargoed_registration(self, user_admin_project_public, public_project_for_registration):
        return RegistrationFactory(project=public_project_for_registration,
                                             creator=user_admin_project_public,
                                             embargo=EmbargoFactory(user=user_admin_project_public))

    @pytest.fixture(autouse=True)
    def collection(self, user_admin_project_public):
        return CollectionFactory(creator=user_admin_project_public)

    @pytest.fixture(autouse=True)
    def osf_provider(self):
        # Note: at least a provider whose _id == 'osf' have to exist for the script to work
        return PreprintProviderFactory(_id='osf', name='osfprovider')

    @pytest.fixture(autouse=True)
    def other_provider(self):
        return PreprintProviderFactory(_id='adl', name='anotherprovider')

    @pytest.fixture(autouse=True)
    def osf_preprint(self, project_for_osf_preprint, user_admin_project_public, osf_provider):
        return PreprintFactory(project=project_for_osf_preprint,
                                             creator=user_admin_project_public,
                                             provider=osf_provider)

    @pytest.fixture(autouse=True)
    def other_preprint(self, project_for_other_preprint, user_admin_project_public, other_provider):
        return PreprintFactory(project=project_for_other_preprint,
                                             creator=user_admin_project_public,
                                             provider=other_provider)

    @pytest.fixture(autouse=True)
    def all_included_links(self, user_admin_project_public, user_admin_project_private, public_project_for_registration,
                             project_for_osf_preprint, project_for_other_preprint,
                             active_registration, other_provider, osf_preprint,
                             other_preprint):
        # Return urls of all fixtures
        urls_to_include = [item['loc'] for item in settings.SITEMAP_STATIC_URLS]
        urls_to_include.extend([
            user_admin_project_public.url,
            user_admin_project_private.url,
            public_project_for_registration.url,
            project_for_osf_preprint.url,
            project_for_other_preprint.url,
            active_registration.url,
            '/preprints/{}/'.format(osf_preprint._id),
            '/preprints/{}/{}/'.format(other_provider._id, other_preprint._id),
            '/project/{}/files/osfstorage/{}/?action=download'.format(osf_preprint.node._id,
                                                                      osf_preprint.primary_file._id),
            '/project/{}/files/osfstorage/{}/?action=download'.format(other_preprint.node._id,
                                                                      other_preprint.primary_file._id),
        ])
        urls_to_include = [urlparse.urljoin(settings.DOMAIN, item) for item in urls_to_include]

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

    def test_collection_link_not_included(self, collection, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urlparse.urljoin(settings.DOMAIN, collection.url) not in urls

    def test_private_project_link_not_included(self, private_project, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urlparse.urljoin(settings.DOMAIN, private_project.url) not in urls

    def test_embargoed_registration_link_not_included(self, embargoed_registration, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urlparse.urljoin(settings.DOMAIN, embargoed_registration.url) not in urls

    def test_deleted_project_link_not_included(self, deleted_project, create_tmp_directory):

        with mock.patch('website.settings.STATIC_FOLDER', create_tmp_directory):
            urls = get_all_sitemap_urls()

        assert urlparse.urljoin(settings.DOMAIN, deleted_project.url) not in urls
