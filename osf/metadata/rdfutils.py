import rdflib
import rdflib.compare

from website import settings as website_settings


# namespace for osf's own concepts:
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
# PID namespaces:
OSFIO = rdflib.Namespace(website_settings.DOMAIN)
DOI = rdflib.Namespace('https://doi.org/')
ORCID = rdflib.Namespace('https://orcid.org/')
ROR = rdflib.Namespace('https://ror.org/')
# standard namespaces we use often:
DCT = rdflib.DCTERMS
FOAF = rdflib.FOAF
OWL = rdflib.OWL
RDF = rdflib.RDF


# vocabularies that will be shortened to prefix form
# (in addition to rdflib's 'core' (rdf, rdfs...))
OSF_CONTEXT = {
    'osf': OSF,
    'dct': DCT,
    'foaf': FOAF,
    'owl': OWL,
}


def contextualized_graph():
    graph = rdflib.Graph()
    for prefix, namespace in OSF_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def try_osfguid_from_iri(iri):
    if iri.startswith(website_settings.DOMAIN):
        path = iri[len(website_settings.DOMAIN):].strip('/')
        if '/' not in path:
            return path
    return None


def checksum_iri(checksum_algorithm, checksum_hex):
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


def format_dct_extent(number_of_bytes: int):
    # following the dcterms:extent recommendation to specify in megabytes
    # https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/extent/
    if number_of_bytes is None or number_of_bytes < 0:
        return None
    number_of_megabytes = number_of_bytes / (2**20)
    return f'{number_of_megabytes:.6} MB'
