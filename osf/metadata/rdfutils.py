import rdflib
import rdflib.compare

from website import settings as website_settings


DCT = rdflib.DCTERMS
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
OSFIO = rdflib.Namespace(website_settings.DOMAIN)


# in addition to rdflib's 'core' (rdf, rdfs, owl...)
OSF_CONTEXT = {
    'osf': OSF,
    'osfio': OSFIO,
    'dct': DCT,
}


# for parsing json:api
JSONAPI_CONTEXT = {
    'id': {'@type': '@id'},
    'data': '@graph',
    'attributes': '@nest',
    'relationships': '@nest',
}


OSFJSONAPI_CONTEXT = {
    **OSF_CONTEXT,
    **JSONAPI_CONTEXT,
}


def contextualized_graph():
    graph = rdflib.Graph()
    for prefix, namespace in OSF_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def guid_irl(guid):
    """return a rdflib.URIRef or None

    "URI": "uniform resource identifier"
    "URL": "uniform resource locator" (a URI that is expected to resolve)
    "IRI": "internationalized resource identifier"
    "IRL": "internationalized resource locator" (an IRI that is expected to resolve)

    @param guid: a string, Guid instance, or another model instance that has a Guid
    @returns rdflib.URIRef or None
    """
    if hasattr(guid, 'guids'):  # quacks like a Guid referent
        guid = guid.guids.first()
    if hasattr(guid, '_id'):  # quacks like a Guid instance
        guid = guid._id
    if not guid:
        return None
    if not isinstance(guid, str):
        raise ValueError('_guid_irl expects str, guid instance, or guid referent')
    return OSFIO[guid]


def try_guid_from_irl(irl):
    if irl.startswith(website_settings.DOMAIN):
        path = irl[len(website_settings.DOMAIN):].strip('/')
        if '/' not in path:
            return path
    return None


def checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)


def graph_equals(actual_rdf_graph, expected_triples):
    expected_rdf_graph = rdflib.Graph()
    for triple in expected_triples:
        expected_rdf_graph.add(triple)
    return rdflib.compare.isomorphic(
        actual_rdf_graph,
        expected_rdf_graph,
    )
