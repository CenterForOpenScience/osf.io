import rdflib

from rest_framework.parsers import JSONParser

from osf.metadata import rdfutils


class JSONAPILDParser(JSONParser):
    """
    Parses a JSON API payload as JSON-LD, into an rdflib.Graph
    """
    media_type = 'application/vnd.api+json'

    def parse(self, stream, media_type=None, parser_context=None):
        return rdflib.Graph().parse(
            data=stream,
            format='json-ld',
            context=rdfutils.JSONAPI_CONTEXT,
        )
