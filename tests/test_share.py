import xml

from mock import patch
from nose.tools import *  # flake8: noqa (PEP8 asserts)
from tests.base import OsfTestCase

from website.search import util
from website.search import share_search

STANDARD_RETURN_VALUE = {
    'hits': {
        'hits': [{
            "_score": 1,
            "_type": "squaredcircle",
            "_id": "1164135",
            "_source": {
                "description": "Jobbers and society.",
                "contributors": [{
                    "name": "Zachary Ryder",
                    "givenName": "Zachary",
                    "familyName": "Ryder",
                    "additionalNames": ["Woo Woo Woo"],
                    "email": "",
                    "sameAs": []
                }],
                "title": "Am I Still Employed",
                "providerUpdatedDateTime": "2014-11-24T00:00:00",
                "uris": {
                    "canonicalUri": "http://squaredcircle.com/zackryder/woowoowoo",
                    "objectUris": ["10.123/wrestlingDOIs"]
                },
                "tags": ['woo', 'woo', 'woo'],
            },
            "_index": "share"
        }, {
            "_score": 1,
            "_type": "squaredcircle",
            "_id": "1164539",
            "_source": {
                "description": "Unlocking the universe with the Cosmic Key",
                "contributors": [{
                    "name": "Star Dust",
                    "givenName": "Star",
                    "familyName": "Dust",
                }],
                "providerUpdatedDateTime": "2014-11-27T00:00:00",
                "uris": {
                    "canonicalUri": "http://squaredcircle.com/stardust/hisssssss"
                },
                "tags": ['cody', 'is', 'noone']
            },
            "_index": "share"
        }],
        'total': 2
    }
}


class TestShareSearch(OsfTestCase):

    @patch.object(share_search.share_es, 'search')
    def test_share_search(self, mock_search):
        mock_search.return_value = {
            'hits': {
                'hits': {},
                'total': 0
            }
        }
        self.app.get('/api/v1/share/search/', params={
            'q': '*',
            'from': '1',
            'size:': '20',
            'sort': 'date',
            'v': '1'
        })
        assert_is(mock_search.called, True)

    @patch.object(share_search.share_es, 'count')
    def test_share_count(self, mock_count):
        mock_count.return_value = {'count': 0}
        self.app.get('/api/v1/share/search/', params={
            'q': '*',
            'from': '1',
            'size:': '20',
            'sort': 'date',
            'count': True,
            'v': '1'
        })
        assert_is(mock_count.called, True)

    def test_share_count_cleans_query(self):
        cleaned_query = share_search.clean_count_query({
            'aggs': {
                'sourceAgg': {
                    'terms': {
                        'field': '_type',
                        'min_doc_count': 0,
                        'size': 0
                    }
                }
            },
            'aggregations': {
                'sourceAgg': {
                    'terms': {
                        'field': '_type',
                        'min_doc_count': 0,
                        'size': 0
                    }
                }
            },
            'from': 0,
            'query':
                {
                    'match_all': {}
                },
            'size': 10
        })
        assert_equals(cleaned_query.keys(), ['query'])


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

    @patch.object(share_search.share_es, 'search')
    def test_atom_returns_200(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/')
        assert_equal(response.status, '200 OK')

    @patch.object(share_search.share_es, 'search')
    def test_atom_renders_xml(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        assert isinstance(xml_content, xml.etree.ElementTree.Element)

    @patch.object(share_search.share_es, 'search')
    def test_atom_head_tag(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        assert_equal(xml_content.tag, '{http://www.w3.org/2005/Atom}feed')

    @patch.object(share_search.share_es, 'search')
    def test_first_link_rel_self(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/')
        xml_content = response.xml
        rel = xml_content.find('{http://www.w3.org/2005/Atom}link')
        assert_equal(rel.attrib['rel'], 'self')

    @patch.object(share_search.share_es, 'search')
    def test_page_5_has_correct_links(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/', params={
            'page': 5
        })
        links = response.xml.findall('{http://www.w3.org/2005/Atom}link')
        assert_equal(len(links), 4)
        attribs = [link.attrib for link in links]
        assert_equal(attribs[1]['href'][-7:], '?page=1')
        assert_equal(attribs[1]['rel'], 'first')
        assert_equal(attribs[2]['href'][-7:], '?page=6')
        assert_equal(attribs[2]['rel'], 'next')
        assert_equal(attribs[3]['href'][-7:], '?page=4')
        assert_equal(attribs[3]['rel'], 'previous')

    @patch.object(share_search.share_es, 'search')
    def test_title_updates_with_query(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/', params={
            'q': 'cats'
        })
        title = response.xml.find('{http://www.w3.org/2005/Atom}title')
        assert_equal(title.text, 'SHARE: Atom Feed for query: "cats"')

    def test_illegal_unicode_sub(self):
        illegal_str = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello'
        illegal_str += unichr(0xd800) + unichr(0xdbff) + ' World'
        assert_equal(util.html_and_illegal_unicode_replace(illegal_str), 'Hello World')
        assert_equal(util.html_and_illegal_unicode_replace(''), '')
        assert_equal(util.html_and_illegal_unicode_replace(None), None)
        assert_equal(util.html_and_illegal_unicode_replace('WOOOooooOOo'), 'WOOOooooOOo')

    def test_html_tag_sub(self):
        html_str = "<p><b>RKO</b> outta <i>NOWHERE</i>!!!</p>"
        assert_equal(util.html_and_illegal_unicode_replace(html_str), 'RKO outta NOWHERE!!!')

    @patch.object(share_search.share_es, 'search')
    def test_atom_returns_correct_number(self, mock_search):
        mock_search.return_value = STANDARD_RETURN_VALUE
        response = self.app.get('/share/atom/')
        entries = response.xml.findall('{http://www.w3.org/2005/Atom}entry')
        assert_equal(len(entries), STANDARD_RETURN_VALUE['hits']['total'])

    def test_compute_start_non_number(self):
        page = 'cow'
        size = 250
        result = util.compute_start(page, size)
        assert_equal(result, 0)

    def test_compute_start_negative(self):
        page = -10
        size = 250
        result = util.compute_start(page, size)
        assert_equal(result, 0)

    def test_compute_start_normal(self):
        page = 50
        size = 10
        result = util.compute_start(page, size)
        assert_equal(result, 490)
