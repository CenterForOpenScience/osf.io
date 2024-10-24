'''helpful constants and functions for working with rdf in osf
'''
import rdflib
import rdflib.compare

from website import settings as website_settings


# namespace for osf's own concepts:
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')  # TODO: publish something helpful there
# namespace for resources on _this_ osf instance (example: `node_iri = OSFIO[node._id]`):
OSFIO = rdflib.Namespace(website_settings.DOMAIN)
# external pid namespaces:
DOI = rdflib.Namespace('https://doi.org/')
DxDOI = rdflib.Namespace('http://dx.doi.org/')  # "earlier but no longer preferred" DOI namespace
ORCID = rdflib.Namespace('https://orcid.org/')
ROR = rdflib.Namespace('https://ror.org/')
# external terminology namespaces:
DCTERMS = rdflib.Namespace('http://purl.org/dc/terms/')                 # "dublin core terms"
DCMITYPE = rdflib.Namespace('http://purl.org/dc/dcmitype/')             # "dublin core metadata initiative type"
FOAF = rdflib.Namespace('http://xmlns.com/foaf/0.1/')                   # "friend of a friend"
OWL = rdflib.Namespace('http://www.w3.org/2002/07/owl#')                # "web ontology language"
RDF = rdflib.Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#')   # "resource description framework"
SKOS = rdflib.Namespace('http://www.w3.org/2004/02/skos/core#')         # "simple knowledge organization system"
DCAT = rdflib.Namespace('http://www.w3.org/ns/dcat#')                   # "data catalog (vocabulary)"
PROV = rdflib.Namespace('http://www.w3.org/ns/prov#')                   # "provenance"
# non-standard namespace for datacite terms (resolves to datacite docs)
DATACITE = rdflib.Namespace('https://schema.datacite.org/meta/kernel-4/#')


# namespace prefixes that will be shortened by default
# when serialized, instead of displaying the full iri
# (in addition to rdflib's 'core' (rdf, rdfs...))
OSF_CONTEXT = {
    'osf': OSF,
    'dcterms': DCTERMS,
    'foaf': FOAF,
    'owl': OWL,
    'skos': SKOS,
    'dcmitype': DCMITYPE,
    'dcat': DCAT,
    'prov': PROV,
}


def contextualized_graph(graph=None) -> rdflib.Graph:
    '''bind default namespace prefixes to a new (or given) rdf graph
    '''
    if graph is None:
        graph = rdflib.Graph()
    for prefix, namespace in OSF_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def checksum_iri(checksum_algorithm, checksum_hex) -> rdflib.URIRef:
    '''encode a checksum-based content address urn

    @checksum_algorithm: str, ideally from https://www.iana.org/assignments/hash-function-text-names/
    @checksum_hex: hexadecimal str
    @return: rdflib.URIRef
    '''
    urn = f'urn:checksum:{checksum_algorithm}::{checksum_hex}'
    return rdflib.URIRef(urn)


def format_dcterms_extent(number_of_bytes: int) -> str:
    '''format filesize value for dcterms:extent

    following the dcterms:extent recommendation to specify in megabytes:
    https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/extent/

    @number_of_bytes: int (filesize in bytes)
    @return: str
    '''
    if number_of_bytes is None or number_of_bytes < 0:
        return None
    number_of_megabytes = number_of_bytes / (2**20)
    # format with variable precision
    assert number_of_megabytes >= 0.0
    if number_of_megabytes > 1.0:
        formatted_number = f'{number_of_megabytes:.1f}'  # precision = 1, e.g. '7.2 MB'
    elif number_of_megabytes > 0.001:
        formatted_number = f'{number_of_megabytes:.3f}'  # precision = 3, e.g. '0.723 MB'
    else:
        formatted_number = f'{number_of_megabytes:.6f}'  # precision = 6, e.g. '0.000123 MB'
    return f'{formatted_number} MB'


def primitivify_rdf(thing):
    '''recursively replace rdflib terms with their primitive python counterparts

    (probably slow on very deeply nested structures,
    utterly unequipped for cyclicly nested structures)

    @thing: dict, list, tuple, rdflib.term.Node, or whatever
    '''
    if isinstance(thing, rdflib.URIRef):
        # replace URIRef object with a primitive URI string
        return str(thing)
    if isinstance(thing, rdflib.Literal):
        # convert literal to python according to its datatype
        primitive = thing.toPython()
        if not isinstance(primitive, (str, int, float)):
            raise ValueError(
                f'primitivify_rdf found a literal ({thing}) with unsupported '
                f'primitive type ({type(thing)}) -- either pre-process it'
                ' or update primitivify_rdf to handle this case.'
            )
        return primitive
    if isinstance(thing, rdflib.BNode):
        raise ValueError(
            f'primitivify_rdf found a blank identifier ({thing}), but explicit'
            ' blank ids are not helpful except within a local graph-space'
            ' -- consider expressing blank ids implicitly, thru data structure.'
        )
    if isinstance(thing, tuple):
        return tuple(
            primitivify_rdf(val)
            for val in thing
        )
    if isinstance(thing, set):
        return {
            primitivify_rdf(val)
            for val in thing
        }
    if isinstance(thing, list):
        return [
            primitivify_rdf(val)
            for val in thing
        ]
    if isinstance(thing, dict):
        return {
            primitivify_rdf(key): primitivify_rdf(val)
            for key, val in thing.items()
        }
    return thing  # end recursion with pass-thru


def without_namespace(iri: rdflib.URIRef, namespace: rdflib.Namespace) -> str:
    assert iri.startswith(namespace)
    return iri[len(namespace):]


def smells_like_iri(maybe_iri: str) -> bool:
    return (
        isinstance(maybe_iri, str)
        and '://' in maybe_iri
    )
