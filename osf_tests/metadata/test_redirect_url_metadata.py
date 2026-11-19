import json

from api_tests.utils import create_test_file
from osf.metadata.rdfutils import OSF, OSFIO
from osf.metadata.tools import pls_gather_metadata_as_dict, pls_gather_metadata_file
from osf.models import AbstractNode
from osf.models.base import coerce_guid
from osf_tests import factories
from tests.base import OsfTestCase

REDIRECT_URL = 'https://example.com/new-home'
RELATION = str(OSF.redirectUrl)


def set_redirect_url(osf_item):
    guid = coerce_guid(osf_item)
    guid.redirect_url = REDIRECT_URL
    guid.save()


class TestRedirectUrlMetadata(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user, is_public=True)

    def each_type_of_resource(self):
        return (
            self.project,
            factories.RegistrationFactory(creator=self.user, is_public=True),
            factories.PreprintFactory(creator=self.user, is_published=True),
        )

    def assert_in_linkset(self, osf_item):
        anchor = f'{OSFIO}{coerce_guid(osf_item)._id}'
        linkset = pls_gather_metadata_file(osf_item, 'linkset').serialized_metadata
        assert f'<{REDIRECT_URL}> ; rel="{RELATION}" ; anchor="{anchor}"' in linkset
        linkset_json = pls_gather_metadata_file(osf_item, 'linkset-json').serialized_metadata
        (entry,) = [entry for entry in json.loads(linkset_json)['linkset'] if RELATION in entry]
        assert entry['anchor'] == anchor
        assert entry[RELATION] == [{'href': REDIRECT_URL}]

    # FAIR signposting

    def test_linkset_without_redirect_url(self):
        assert RELATION not in pls_gather_metadata_file(self.project, 'linkset').serialized_metadata
        linkset_json = pls_gather_metadata_file(self.project, 'linkset-json').serialized_metadata
        assert RELATION not in linkset_json

    def test_linkset(self):
        for osf_item in self.each_type_of_resource():
            set_redirect_url(osf_item)
            self.assert_in_linkset(osf_item)

    def test_linkset_of_file_inherits_redirect_url(self):
        file = create_test_file(self.project, self.user, filename='blarg.txt')
        set_redirect_url(self.project)
        self.assert_in_linkset(file)

    def test_linkset_of_soft_deleted_project(self):
        set_redirect_url(self.project)
        AbstractNode.objects.filter(pk=self.project.pk).update(is_deleted=True)  # marked as deleted, still in the db
        for format_key in ('linkset', 'linkset-json'):
            res = self.app.get(f'/metadata/{self.project._id}/?format={format_key}')
            assert res.status_code == 200
            assert REDIRECT_URL in res.get_data(as_text=True)

    # schema.org json-ld

    def test_google_dataset_without_redirect_url(self):
        assert 'redirectUrl' not in pls_gather_metadata_as_dict(self.project, 'google-dataset-json-ld')

    def test_google_dataset(self):
        for osf_item in self.each_type_of_resource():
            set_redirect_url(osf_item)
            metadata = pls_gather_metadata_as_dict(osf_item, 'google-dataset-json-ld')
            assert metadata['redirectUrl'] == REDIRECT_URL

    def test_google_dataset_of_file_inherits_redirect_url(self):
        file = create_test_file(self.project, self.user, filename='blarg.txt')
        set_redirect_url(self.project)
        assert pls_gather_metadata_as_dict(file, 'google-dataset-json-ld')['redirectUrl'] == REDIRECT_URL

    # DataCite

    def test_datacite_is_unchanged(self):
        """the xml is validated against the DataCite schema,
        so neither it nor the json should change just because a guid redirects
        """
        self.project.set_identifier_value(category='doi', value=f'10.70102/FK2osf.io/{self.project._id}')
        format_keys = ('datacite-xml', 'datacite-json')
        without_redirect_url = {
            format_key: pls_gather_metadata_file(self.project, format_key).serialized_metadata
            for format_key in format_keys
        }
        set_redirect_url(self.project)
        for format_key in format_keys:
            with_redirect_url = pls_gather_metadata_file(self.project, format_key).serialized_metadata
            assert with_redirect_url == without_redirect_url[format_key], format_key
