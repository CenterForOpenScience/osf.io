import re
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer, StaticHTMLRenderer


class JSONRendererWithESISupport(JSONRenderer):
    format = 'json'
    media_type = 'application/json'
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        initial_rendering = super(JSONRendererWithESISupport, self).render(data, accepted_media_type, renderer_context)
        augmented_rendering = re.sub(r'"<esi:include src=\\"(.*?)\\"\/>"', '<esi:include src="\1"/>', initial_rendering.decode())
        return augmented_rendering

class JSONAPIRenderer(JSONRendererWithESISupport):
    format = 'jsonapi'
    media_type = 'application/vnd.api+json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Allow adding a top-level `meta` object to the response by including it in renderer_context
        # See JSON-API documentation on meta information: http://jsonapi.org/format/#document-meta
        data_type = type(data)
        if renderer_context is not None and data_type != str and data is not None:
            meta_dict = renderer_context.get('meta', {})
            version = getattr(renderer_context['request'], 'version', None)
            warning = renderer_context['request'].META.get('warning', None)
            if version:
                meta_dict['version'] = version
            if warning:
                meta_dict['warning'] = warning
            data.setdefault('meta', {}).update(meta_dict)
        return super(JSONAPIRenderer, self).render(data, accepted_media_type, renderer_context)


class BrowsableAPIRendererNoForms(BrowsableAPIRenderer):
    """
    Renders browsable API but omits HTML forms
    """

    def show_form_for_method(self, view, method, request, obj):
        return False


class PlainTextRenderer(StaticHTMLRenderer):
    """
    Renders plain text.

    Inherits from StaticHTMLRenderer for error handling.
    """

    media_type = 'text/markdown'
    format = 'txt'
