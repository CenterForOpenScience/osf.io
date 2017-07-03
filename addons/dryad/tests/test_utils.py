from nose.tools import *  # noqa

from addons.dryad.tests.utils import DryadTestRepository, DryadTestCase


class DryadTestUtils(DryadTestCase):

    def setUp(self):
        super(DryadTestCase, self).setUp()
        self.repository = DryadTestRepository()

    def test_get_dryad_title(self):
        resp = self.repository.get_dryad_title(doi='10.5061/dryad.1850')
        assert_true('phylogeny' in resp)

    def test_check_dryad_doi(self):
        resp = self.repository.check_dryad_doi(doi='10.5061/dryad.1850')
        assert_true(resp)
        resp = self.repository.check_dryad_doi(doi='THIS IS A BAD DOI')
        assert_false(resp)

    def test_list_dryad_dois(self):
        resp = self.repository.list_dryad_dois()
        assert_true(len(resp.getElementsByTagName('identifier')) == 20)

    def test_get_dryad_search_results_json_formatted(self):
        # TODO. This has yet to be implemented
        assert True
        return
        resp = self.repository.get_dryad_search_results_json_formatted(start_n=0,
            count=10,
            query='Phylogenetic')
        assert_true(resp['count'] == 10)
        assert_true(resp['start'] == 0)
        assert_true(len(resp['package_list']) == resp['count'])
