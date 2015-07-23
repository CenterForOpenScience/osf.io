from rest_framework.negotiation import BaseContentNegotiation


class CustomClientContentNegotiation(BaseContentNegotiation):
    def select_parser(self, request, parsers):
        """
        Select parser whose media_type matches content_type
        """
        content_type = request.QUERY_PARAMS.get('content_type', request.content_type)
        for parser in parsers:
            if parser.media_type == content_type:
                return parser
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix):
        """
        Select the third renderer in the `.renderer_classes` list for the browsable API,
        otherwise use the first renderer which has media_type "application/vnd.api+json"
        """
        if 'text/html' in request.META.get('HTTP_ACCEPT', 'None'):
            return (renderers[2], renderers[2].media_type)
        return (renderers[0], renderers[0].media_type)
