from nose.tools import *  # flake8: noqa
from tests.base import OsfTestCase
from tests.factories import InstitutionFactory

class TestInstitution(OsfTestCase):
    def setUp(self):
        super(TestInstitution, self).setUp()
        self.institution = InstitutionFactory()

    def test_institution_save_only_changes_mapped_fields_on_node(self):
        node = self.institution.node
        old = {
            'title': node.title,
            'institution_logo_name': node.institution_logo_name,
            'system_tags': node.system_tags,
            'piwik_site_id': node.piwik_site_id
        }
        new = {
            'title': ' A Completely Different name omg.',
            'institution_logo_name': ' A different ',
            'system_tags': ['new_tags', 'other', 'busta', 'rhymes'],
            'piwik_site_id': 'is this an id'
        }
        self.institution.name = new['title']
        self.institution.logo_name = new['institution_logo_name']
        self.institution.system_tags = new['system_tags']
        self.institution.piwik_site_id = new['piwik_site_id']
        self.institution.save()

        node.reload()
        #assert changes
        assert_equal(node.title, new['title'])
        assert_equal(node.institution_logo_name, new['institution_logo_name'])

        #assert remained same
        assert_equal(node.system_tags, old['system_tags'])
        assert_not_equal(node.system_tags, new['system_tags'])
        assert_equal(node.piwik_site_id, old['piwik_site_id'])
        assert_not_equal(node.piwik_site_id, new['piwik_site_id'])

    def test_institution_mappings(self):
        for key, val in self.institution.attribute_map.iteritems():
            assert_equal(getattr(self.institution, key), getattr(self.institution.node, val))

    def test_institution_banner_path_none(self):
        inst = InstitutionFactory()
        inst.banner_name = None
        assert_is_none(inst.banner_path, None)

    def test_institution_logo_path_none(self):
        inst = InstitutionFactory()
        inst.logo_name = None
        assert_is_none(inst.logo_path, None)
