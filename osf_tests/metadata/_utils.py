import rdflib

from osf.metadata import gather
from osf.metadata.rdfutils import contextualized_graph

def assert_triples(actual_triples, expected_triples):
    _expected_graph, _expected_focuses = _get_graph_and_focuses(expected_triples)
    _actual_graph, _actual_focuses = _get_graph_and_focuses(actual_triples)
    assert_graphs_equal(_actual_graph, _expected_graph)
    assert _expected_focuses == _actual_focuses


def assert_graphs_equal(actual_rdflib_graph, expected_rdflib_graph):
    (_overlap, _expected_but_absent, _unexpected_but_present) = rdflib.compare.graph_diff(
        expected_rdflib_graph,
        actual_rdflib_graph,
    )
    assert not _expected_but_absent and not _unexpected_but_present, '\n\t'.join((
        'unequal triple-sets!',
        f'overlap size: {len(_overlap)}',
        f'expected (but absent): {_friendly_graph(_expected_but_absent)}',
        f'unexpected (but present): {_friendly_graph(_unexpected_but_present)}',
    ))


def _get_graph_and_focuses(triples):
    _graph = rdflib.Graph()
    _focuses = set()
    for (subj, pred, obj) in triples:
        if isinstance(obj, gather.Focus):
            _graph.add((subj, pred, obj.iri))
            _focuses.add(obj)
        else:
            _graph.add((subj, pred, obj))
    return _graph, _focuses


def _friendly_graph(rdfgraph) -> str:
    _graph_to_print = contextualized_graph(rdfgraph)
    _delim = '\n\t\t'
    return _delim + _delim.join(
        ' '.join(_term.n3() for _term in triple)
        for triple in _graph_to_print
    )
