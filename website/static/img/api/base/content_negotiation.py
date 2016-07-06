
from rest_framework.negotiation import DefaultContentNegotiation


class JSONAPIContentNegotiation(DefaultContentNegotiation):

    def select_renderer(self, request, renderers, format_suffix=None):
        """
        Returns appropriate tuple (renderer, media type).

        If 'application/json' in acceptable media types, use the first renderer in
        DEFAULT_RENDERER_CLASSES which should be 'api.base.renderers.JSONAPIRenderer'.
        Media_type "application/vnd.api+json".  Otherwise, use default select_renderer.
        """
        accepts = self.get_accept_list(request)

        if 'application/json' in accepts:
            return (renderers[0], renderers[0].media_type)

        return super(JSONAPIContentNegotiation, self).select_renderer(request, renderers)
