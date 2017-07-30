import os

import pytest
import mock
import shutil, xml, urlparse

from scripts import generate_sitemap
from osf_tests import factories
from website import settings


def get_all_sitemap_urls():
    # Create temporary directory for the sitemaps to be generated

    generate_sitemap.main()

    # Parse the generated XML sitemap file
    with open('sitemaptmpfolder' + '/sitemaps' + '/sitemap_0.xml') as f:
        tree = xml.etree.ElementTree.parse(f)

    # Remove the temp directory
    shutil.rmtree('sitemaptmpfolder')

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
    def public_project_for_active_registration(self, public_project_owner):
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
    def active_registration(self, public_project_owner, public_project_for_active_registration):
        return factories.RegistrationFactory(project=public_project_for_active_registration,
                                             creator=public_project_owner,
                                             is_public=True)

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


    def generate_all_links(self):
    def static_urls(self):
        # Returns a list of static urls that should be included
        return [urlparse.urljoin(settings.DOMAIN, item['loc']) for item in settings.SITEMAP_STATIC_URLS]


    def user_urls(self, public_project_owner, private_project_owner):
        # Returns a list of user urls that should be included
        list = [
            public_project_owner.url,
            private_project_owner.url,
        ]
        return [urlparse.urljoin(settings.DOMAIN, item) for item in list]


    def public_project_urls(self, public_project_for_active_registration, project_for_osf_preprint,
                            project_for_other_preprint):
        # Returns a list of public project urls that should be included
        list = [
            public_project_for_active_registration.url,
            project_for_osf_preprint.url,
            project_for_other_preprint.url
        ]
        return [urlparse.urljoin(settings.DOMAIN, item) for item in list]


    def private_project_url(self, private_project):
        # Returns the private project url that should NOT be included
        return urlparse.urljoin(settings.DOMAIN, private_project.url)


    def active_registration_urls(self, active_registration):
        # Returns a list of active registration urls that should be included
        return [urlparse.urljoin(settings.DOMAIN, active_registration.url)]


    def collection_url(self, collection):
        # Returns the retracted registration url that should NOT be included
        return urlparse.urljoin(settings.DOMAIN, collection.url)


    def preprint_related_urls(self, osf_preprint, other_preprint, other_provider):
        # Returns a list of preprint related urls that should be included
        list = [
            '/preprints/{}/'.format(osf_preprint._id),
            '/preprints/{}/{}/'.format(other_provider._id, other_preprint._id),
            '/project/{}/files/osfstorage/{}/?action=download'.format(osf_preprint.node._id,
                                                                      osf_preprint.primary_file._id),
            '/project/{}/files/osfstorage/{}/?action=download'.format(other_preprint.node._id,
                                                                      other_preprint.primary_file._id),
        ]
        return [urlparse.urljoin(settings.DOMAIN, item) for item in list]


    def test_all_links_included(self):

        with mock.patch('website.settings.STATIC_FOLDER', 'sitemaptmpfolder'):
            urls = get_all_sitemap_urls()

        urls_to_include = [item['loc'] for item in settings.SITEMAP_STATIC_URLS]
        urls_to_include.extend([
            public_project_owner.url,
            private_project_owner.url,
            public_project_for_active_registration.url,
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
        assert len(urls_to_include) == len(urls)
        assert set(urls_to_include) == set(urls)

    #def test_collection_links_included(self, public_project_owner, private_project_owner,
    #                            public_project_for_active_registration, project_for_osf_preprint,
    #                            project_for_other_preprint, active_registration,
    #                            osf_preprint, osf_provider, other_preprint, other_provider):