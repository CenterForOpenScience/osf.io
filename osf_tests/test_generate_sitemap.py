import os

import pytest
import mock
import shutil, tempfile, xml, urlparse

from scripts import generate_sitemap
from osf_tests import factories
from website import settings


def get_all_sitemap_urls():
    # Create temporary directory for the sitemaps to be generated

    generate_sitemap.main()

    # Parse the generated XML sitemap file
    with open(settings.STATIC_FOLDER + '/sitemaps' + '/sitemap_0.xml') as f:
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
    def public_project_owner(self):
        return factories.AuthUserFactory()

    @pytest.fixture(autouse=True)
    def private_project_owner(self):
        return factories.AuthUserFactory()

    @pytest.fixture(autouse=True)
    def public_project_for_registration(self, public_project_owner):
        return factories.ProjectFactory(creator=public_project_owner, is_public=True)

    @pytest.fixture(autouse=True)
    def project_for_osf_preprint(self, public_project_owner):
        return factories.ProjectFactory(creator=public_project_owner, is_public=True)

    @pytest.fixture(autouse=True)
    def project_for_other_preprint(self, public_project_owner):
        return factories.ProjectFactory(creator=public_project_owner, is_public=True)

    @pytest.fixture(autouse=True)
    def private_project(self, private_project_owner):
        return factories.ProjectFactory(creator=private_project_owner, is_public=False)

    @pytest.fixture(autouse=True)
    def deleted_project(self, public_project_owner):
        return factories.ProjectFactory(creator=public_project_owner, is_deleted=True)

    @pytest.fixture(autouse=True)
    def active_registration(self, public_project_owner, public_project_for_registration):
        return factories.RegistrationFactory(project=public_project_for_registration,
                                             creator=public_project_owner,
                                             is_public=True)

    @pytest.fixture(autouse=True)
    def embargoed_registration(self, public_project_owner, public_project_for_registration):
        return factories.RegistrationFactory(project=public_project_for_registration,
                                             creator=public_project_owner,
                                             embargo=factories.EmbargoFactory(user=public_project_owner))

    @pytest.fixture(autouse=True)
    def collection(self, public_project_owner):
        return factories.CollectionFactory(creator=public_project_owner)

    @pytest.fixture(autouse=True)
    def osf_provider(self):
        # Note: at least a provider whose _id == 'osf' have to exist for the script to work
        return factories.PreprintProviderFactory(_id='osf', name='osfprovider')

    @pytest.fixture(autouse=True)
    def other_provider(self):
        return factories.PreprintProviderFactory(_id='adl', name="anotherprovider")

    @pytest.fixture(autouse=True)
    def osf_preprint(self, project_for_osf_preprint, public_project_owner, osf_provider):
        return factories.PreprintFactory(project=project_for_osf_preprint,
                                             creator=public_project_owner,
                                             provider=osf_provider)

    @pytest.fixture(autouse=True)
    def other_preprint(self, project_for_other_preprint, public_project_owner, other_provider):
        return factories.PreprintFactory(project=project_for_other_preprint,
                                             creator=public_project_owner,
                                             provider=other_provider)

    @pytest.fixture(autouse=True)
    def all_included_links(self, public_project_owner, private_project_owner, public_project_for_registration,
                             project_for_osf_preprint, project_for_other_preprint,
                             active_registration, other_provider, osf_preprint,
                             other_preprint):
        # Return urls of all fixtures
        urls_to_include = [item['loc'] for item in settings.SITEMAP_STATIC_URLS]
        urls_to_include.extend([
            public_project_owner.url,
            private_project_owner.url,
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
