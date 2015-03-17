from nose.tools import *  # PEP8 asserts
from mock import patch
from tests.base import OsfTestCase
import xml

from website.search import share_search


class TestShareSearch(OsfTestCase):

    @patch.object(share_search.share_es, 'search')
    def test_share_search(self, mock_search):
        mock_search.return_value = {
            'hits': {
                'hits': {},
                'total': 0
            }
        }
        self.app.get('/api/v1/share/', params={
            'q': '*',
            'from': '1',
            'size:': '20',
            'sort': 'date'
        })
        assert_is(mock_search.called, True)

    @patch.object(share_search.share_es, 'count')
    def test_share_count(self, mock_count):
        mock_count.return_value = {'count': 0}
        self.app.get('/api/v1/share/', params={
            'q': '*',
            'from': '1',
            'size:': '20',
            'sort': 'date',
            'count': True
        })
        assert_is(mock_count.called, True)

    @patch.object(share_search.share_es, 'search')
    def test_share_providers(self, mock_search):
        mock_search.return_value = {
            'hits': {
                'hits': {},
                'total': 0
            }
        }
        self.app.get('/api/v1/share/providers/')
        assert_is(mock_search.called, True)

    @patch.object(share_search.share_es, 'search')
    def test_share_stats(self, mock_search):
        mock_search.return_value = {
            'hits': {
                'hits': {},
                'total': 0
            },
            'aggregations': {
                'date_chunks': {
                    'buckets': [{
                        'articles_over_time': {
                            'buckets': []
                        },
                        'key': 'test',
                        'doc_count': 0
                    }]
                },
                'sources': {
                    'buckets': [{
                        'key': 'test',
                        'doc_count': 0
                    }]
                },
                'earlier_documents': {
                    'sources': {
                        'buckets': [{
                            'key': 'test',
                            'doc_count': 0
                        }]
                    }
                }
            }
        }
        self.app.get('/api/v1/share/stats/')
        assert_is(mock_search.called, True)


class TestShareAtom(OsfTestCase):

    def test_atom_returns_200(self):
        response = self.app.get('/share/atom/')
        assert_equal(response.status, '200 OK')

    def test_atom_renders_xml(self):
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        assert isinstance(xml_content, xml.etree.ElementTree.Element)

    def test_atom_head_tag(self):
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        assert_equal(xml_content.tag, '{http://www.w3.org/2005/Atom}feed')

    def test_first_link_rel_self(self):
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        rel = xml_content.find('{http://www.w3.org/2005/Atom}link')
        assert_equal(rel.attrib['rel'], 'self')

    def test_page_5_has_correct_links(self):
        response = self.app.get('/share/atom/', params={
            'page': 5
        })
        links = response.xml.findall('{http://www.w3.org/2005/Atom}link')
        assert_equal(len(links), 4)
        attribs = [link.attrib for link in links]
        assert_equal(attribs[1]['href'], 'http://localhost:5000/share/atom/?page=1')
        assert_equal(attribs[1]['rel'], 'first')
        assert_equal(attribs[2]['href'], 'http://localhost:5000/share/atom/?page=6')
        assert_equal(attribs[2]['rel'], 'next')
        assert_equal(attribs[3]['href'], 'http://localhost:5000/share/atom/?page=4')
        assert_equal(attribs[3]['rel'], 'previous')

    def test_title_updates_with_query(self):
        response = self.app.get('/share/atom/', params={
            'q': 'cats'
        })
        title = response.xml.find('{http://www.w3.org/2005/Atom}title')
        assert_equal(title.text, 'SHARE: Atom Feed for query: "cats"')
