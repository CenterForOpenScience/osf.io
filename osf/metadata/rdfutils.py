import rdflib

from website import settings as website_settings


OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
OSFIO = rdflib.Namespace('https://osf.io/')


OSF_CONTEXT = {
    'osf': OSF,
    'osfio': OSFIO,
    'dct': rdflib.DCTERMS,
    'rdf': rdflib.RDF,
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


def osf_namespace_manager():
    namespace_manager = rdflib.NamespaceManager(rdflib.Graph())
    for prefix, namespace in OSF_CONTEXT:
        namespace_manager.bind(prefix, namespace)
    return namespace_manager


def contextualized_graph():
    return rdflib.Graph(namespace_manager=osf_namespace_manager())


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
        return None  # politely skipple this triple
    if not isinstance(guid, str):
        raise ValueError('_guid_irl expects str, guid instance, or guid referent')
    return rdflib.URIRef(guid, base=website_settings.DOMAIN)


def try_guid_from_irl(irl):
    if isinstance(irl, rdflib.URIRef) and irl.startswith(website_settings.DOMAIN):
        path = irl[len(website_settings.DOMAIN):].strip('/')
        if '/' not in path:
            return path
    return None


def checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)
