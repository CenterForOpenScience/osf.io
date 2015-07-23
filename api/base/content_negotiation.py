from rest_framework.negotiation import DefaultContentNegotiation


class CustomClientContentNegotiation(DefaultContentNegotiation):

    def select_renderer(self, request, renderers, format_suffix):
        """
        Select the third renderer in the `.renderer_classes` list for the browsable API,
        otherwise use the first renderer which has media_type "application/vnd.api+json"
        """
        if 'text/html' in request.META.get('HTTP_ACCEPT', 'None'):
            return (renderers[2], renderers[2].media_type)
        return (renderers[0], renderers[0].media_type)
