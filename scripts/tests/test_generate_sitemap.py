import pytest

import shutil, tempfile, xml, os
from urlparse import urljoin
from website import settings
from scripts.generate_sitemap import main
from osf_tests.factories import AuthUserFactory, PreprintProviderFactory, PreprintFactory, ProjectFactory, \
    RegistrationFactory, CollectionFactory

@pytest.mark.django_db
class TestGenerateSitemap:

    def test_all_links_are_included(self):
        # Create temporary directory for the sitemaps to be generated
        temp_dir = tempfile.mkdtemp()

        # Set static folder to the path of temp_dir, so that the generator would store the sitemaps under
        # <path_to_temp_dir>/sitemaps/
        settings.STATIC_FOLDER = temp_dir

        # Test setup
        user_1 = AuthUserFactory()
        user_2 = AuthUserFactory()
        project_1 = ProjectFactory(creator=user_1)
        project_2 = ProjectFactory(creator=user_2)
        registration_1 = RegistrationFactory(project=project_1, creator=user_1, is_public=True)
        registration_2 = RegistrationFactory(project=project_2, creator=user_2, is_public=True)
        provider_1 = PreprintProviderFactory(_id='osf', name='osfprovider')
        provider_2 = PreprintProviderFactory(_id='adl', name="anotherprovider")
        preprint_1 = PreprintFactory(provider=provider_1, project=project_1, creator=user_1)
        preprint_2 = PreprintFactory(provider=provider_2, project=project_2, creator=user_2)

        # Constructed list of urls that should be included
        list_of_urls = [urljoin(settings.DOMAIN, item['loc']) for item in settings.SITEMAP_STATIC_URLS]
        list_of_urls.extend([urljoin(settings.DOMAIN, user_1._id), urljoin(settings.DOMAIN, user_2._id)])
        list_of_urls.extend([urljoin(settings.DOMAIN, project_1._id),
                             urljoin(settings.DOMAIN, project_2._id),
                             urljoin(settings.DOMAIN, registration_1._id),
                             urljoin(settings.DOMAIN, registration_2._id)])
        list_of_urls.extend([settings.DOMAIN + 'preprints/' + preprint_1._id + '/',
                             settings.DOMAIN + 'preprints/' + provider_2._id + '/' + preprint_2._id + '/'])

        url_preprint_file_1 = os.path.join(
                            settings.DOMAIN,
                            'project',
                            preprint_1.node._id,   # Parent node id
                            'files',
                            'osfstorage',
                            preprint_1.primary_file._id,  # Preprint file deep_url
                            '?action=download'
                        )

        url_preprint_file_2 = os.path.join(
                            settings.DOMAIN,
                            'project',
                            preprint_2.node._id,   # Parent node id
                            'files',
                            'osfstorage',
                            preprint_2.primary_file._id,  # Preprint file deep_url
                            '?action=download'
                        )

        list_of_urls.extend([url_preprint_file_1, url_preprint_file_2])

        # Run the script
        main()

        # Parse the generated XML sitemap file
        with open(temp_dir + '/sitemaps' + '/sitemap_0.xml') as f:
            tree = xml.etree.ElementTree.parse(f)

        # Remove the temp directory
        shutil.rmtree(temp_dir)

        # Get all the urls in the sitemap
        # Note: namespace was defined in the XML file, therefore necessary to include in tag
        namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        urls = [element.text for element in tree.iter(namespace + 'loc')]

        # Check and see if all urls are included
        assert set(list_of_urls) == set(urls)

    def test_collection_links_not_included(self):
        # Create temporary directory for the sitemaps to be generated
        temp_dir = tempfile.mkdtemp()

        # Set static folder to the path of temp_dir, so that the generator would store the sitemaps under
        # <path_to_temp_dir>/sitemaps/
        settings.STATIC_FOLDER = temp_dir

        # Generation script requires at least one PreprintProvider with id = osf
        provider = PreprintProviderFactory(_id='osf', name='osfprovider')

        # Create a collection, whose link should not be included in the sitemap
        collection = CollectionFactory()
        collection_link = urljoin(settings.DOMAIN, collection._id)

        # Run the script
        main()

        # Parse the generated XML sitemap file
        with open(temp_dir + '/sitemaps' + '/sitemap_0.xml') as f:
            tree = xml.etree.ElementTree.parse(f)

        # Remove the temp directory
        shutil.rmtree(temp_dir)

        # Get all the urls in the sitemap
        # Note: namespace was defined in the XML file, therefore necessary to include in tag
        namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
        urls = [element.text for element in tree.iter(namespace + 'loc')]

        assert collection not in urls