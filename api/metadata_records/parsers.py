import rdflib

from rest_framework.parsers import JSONParser


class JSONAPILDParser(JSONParser):
    """
    Parses a JSON API payload as JSON-LD, into an rdflib.Graph
    """
    media_type = 'application/vnd.api+json'

    JSONLD_CONTEXT = {
        'osf': 'https://osf.io/vocab/2022/',
        'osfio': 'https://osf.io/',
        'dct': 'http://purl.org/dc/terms/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',

        # for parsing json:api
        'id': {'@type': '@id'},
        'data': '@graph',
        'attributes': '@nest',
        'relationships': '@nest',
    }

    def parse(self, stream, media_type=None, parser_context=None):
        return rdflib.Graph().parse(
            data=stream,
            format='json-ld',
            context=self.JSONLD_CONTEXT,
        )
