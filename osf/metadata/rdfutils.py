'''helpful constants and functions for working with rdf in osf
'''
import rdflib
import rdflib.compare

from website import settings as website_settings


# namespace for osf's own concepts:
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
# namespace for resources on _this_ osf instance:
OSFIO = rdflib.Namespace(website_settings.DOMAIN)
# external pid namespaces:
DOI = rdflib.Namespace('https://doi.org/')
ORCID = rdflib.Namespace('https://orcid.org/')
ROR = rdflib.Namespace('https://ror.org/')
# external terminology namespaces:
DCT = rdflib.DCTERMS
FOAF = rdflib.FOAF
OWL = rdflib.OWL
RDF = rdflib.RDF


# namespace prefixes that will be shortened by default
# when serialized, instead of displaying the full iri
# (in addition to rdflib's 'core' (rdf, rdfs...))
OSF_CONTEXT = {
    'osf': OSF,
    'dct': DCT,
    'foaf': FOAF,
    'owl': OWL,
}


def contextualized_graph() -> rdflib.Graph:
    '''get a new rdf graph with default namespace prefixes already bound
    '''
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


def format_dct_extent(number_of_bytes: int) -> str:
    '''format filesize value for dct:extent

    following the dcterms:extent recommendation to specify in megabytes:
    https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/extent/

    @number_of_bytes: int (filesize in bytes)
    @return: str
    '''
    if number_of_bytes is None or number_of_bytes < 0:
        return None
    number_of_megabytes = number_of_bytes / (2**20)

    # format with variable precision
    if number_of_megabytes >= 1.0:      # precision = 1, e.g. '7.2 MB'
        formatted_number = f'{number_of_megabytes:.1f}'
    elif number_of_megabytes >= 0.001:  # precision = 3, e.g. '0.723 MB'
        formatted_number = f'{number_of_megabytes:.3f}'
    else:                               # precision = 6, e.g. '0.000123 MB'
        formatted_number = f'{number_of_megabytes:.6f}'
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
    if isinstance(thing, list):
        return [
            primitivify_rdf(val)
            for val in thing
        ]
    if isinstance(thing, dict):
        return {
            key: primitivify_rdf(val)
            for key, val in thing.items()
        }
    return thing  # end recursion with pass-thru


def without_namespace(iri: rdflib.URIRef, namespace: rdflib.Namespace) -> str:
    assert iri.startswith(namespace)
    return iri[len(namespace):]
