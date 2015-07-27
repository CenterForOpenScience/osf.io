from rest_framework import exceptions
from rest_framework.utils.mediatypes import _MediaType
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.utils.mediatypes import order_by_precedence, media_type_matches


class CustomClientContentNegotiation(DefaultContentNegotiation):

    def select_renderer(self, request, renderers, format_suffix):
        """
        If 'application/json' in acceptable media types, use the JSONAPIRenderer with
        media_type "application/vnd.api+json".  Otherwise, check media types against
        each renderer.  Returns a tuple (renderer, media_type).
        """
        format_query_param = self.settings.URL_FORMAT_OVERRIDE
        format = format_suffix or request.query_params.get(format_query_param)

        if format:
            renderers = self.filter_renderers(renderers, format)

        accepts = self.get_accept_list(request)

        if 'application/json' in accepts:
            return (renderers[0], renderers[0].media_type)

        for media_type_set in order_by_precedence(accepts):
            for renderer in renderers:
                for media_type in media_type_set:
                    if media_type_matches(renderer.media_type, media_type):
                        if (
                            _MediaType(renderer.media_type).precedence >
                            _MediaType(media_type).precedence
                        ):
                            return renderer, renderer.media_type
                        else:
                            return renderer, media_type

        raise exceptions.NotAcceptable(available_renderers=renderers)
