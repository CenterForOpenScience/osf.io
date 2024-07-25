import pytest
import rdflib

from osf.metadata import rdfutils
from website import settings as website_settings


def test_contextualized_graph():
    shouldbe_graph = rdfutils.contextualized_graph()
    assert isinstance(shouldbe_graph, rdflib.Graph)

    url_prefix_tests = {
        'https://osf.io/vocab/2022/blarg': ('osf', rdflib.URIRef(rdfutils.OSF), 'blarg'),
        'http://purl.org/dc/terms/blarg': ('dcterms', rdflib.URIRef(rdfutils.DCTERMS), 'blarg'),
        'http://xmlns.com/foaf/0.1/blarg': ('foaf', rdflib.URIRef(rdfutils.FOAF), 'blarg'),
        'http://www.w3.org/2002/07/owl#blarg': ('owl', rdflib.URIRef(rdfutils.OWL), 'blarg'),
    }
    for url, prefixed in url_prefix_tests.items():
        shouldbe_prefixed = shouldbe_graph.compute_qname(rdflib.URIRef(url), generate=False)
        assert prefixed == shouldbe_prefixed

    # should leave these whole:
    unprefixed_url_tests = {
        'https://osf.io/blarg',
        f'{website_settings.DOMAIN}blarg',
    }
    for unprefixed_url in unprefixed_url_tests:
        with pytest.raises(KeyError):
            shouldbe_graph.compute_qname(rdflib.URIRef(unprefixed_url), generate=False)

def test_checksum_iri():
    checksum_tests = {
        ('blargle', 'plop'): rdflib.URIRef('urn:checksum:blargle::plop'),
        ('sha-256', 'd44af081aee76deb5ecf4478d2f6c23704eeb8644c9c021976b2c054b09af496'):
        rdflib.URIRef('urn:checksum:sha-256::d44af081aee76deb5ecf4478d2f6c23704eeb8644c9c021976b2c054b09af496'),
    }
    for args, expected_iri in checksum_tests.items():
        actual_iri = rdfutils.checksum_iri(*args)
        assert actual_iri == expected_iri


def test_format_dcterms_extent():
    extent_tests = {
        0: '0.000000 MB',
        1: '0.000001 MB',
        439939: '0.420 MB',
        103388383: '98.6 MB',
        7793939377719888: '7432879808.2 MB',
        None: None,
        -9: None,
    }
    for number_of_bytes, expected_extent in extent_tests.items():
        assert rdfutils.format_dcterms_extent(number_of_bytes) == expected_extent


def test_primitivify_rdf():
    primitivify_tests = [
        {'in': 7, 'out': 7},
        {'in': None, 'out': None},
        {'in': 'woop', 'out': 'woop'},
        {'in': [rdflib.Literal('hello'), 'goodbye'], 'out': ['hello', 'goodbye']},
        {'in': rdfutils.DCTERMS.Agent, 'out': 'http://purl.org/dc/terms/Agent'},
        {
            'in': ('a', ['b', rdfutils.DCTERMS.title]),
            'out': ('a', ['b', 'http://purl.org/dc/terms/title']),
        },
        {
            'in': {
                'blah': 'blip',
                rdfutils.DCTERMS.description: ('a', ['b', rdfutils.DCTERMS.title], 78),
                rdfutils.OSF.warb: {
                    rdfutils.OSF.warbly: {
                        rdfutils.OSF.warbl: {'seven', 7},
                    },
                    rdfutils.OSF.warbl: {
                        rdfutils.OSF.warbly: {
                            rdfutils.OWL.sameAs: {'clod', 'blod', 'alod'},
                        },
                    },
                },
            },
            'out': {
                'blah': 'blip',
                'http://purl.org/dc/terms/description': ('a', ['b', 'http://purl.org/dc/terms/title'], 78),
                'https://osf.io/vocab/2022/warb': {
                    'https://osf.io/vocab/2022/warbly': {
                        'https://osf.io/vocab/2022/warbl': {'seven', 7},
                    },
                    'https://osf.io/vocab/2022/warbl': {
                        'https://osf.io/vocab/2022/warbly': {
                            'http://www.w3.org/2002/07/owl#sameAs': {'clod', 'blod', 'alod'},
                        },
                    },
                },
            },
        },
    ]
    for test_case in primitivify_tests:
        actual_out = rdfutils.primitivify_rdf(test_case['in'])
        assert actual_out == test_case['out']

    # explicit blank nodes forbidden (not primitive enough)
    should_raise_error = [
        rdflib.BNode(),
        [1, 2, rdflib.BNode()],
        {'la': {'de': {'da': {'de': {'do': rdflib.BNode()}}}}},
        ({(9, (8, rdflib.BNode())), 7}),
        {'di': {rdflib.BNode(): 'hi'}},
    ]
    for errory_input in should_raise_error:
        with pytest.raises(ValueError):
            rdfutils.primitivify_rdf(errory_input)
