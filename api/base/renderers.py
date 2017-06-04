import re
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer, StaticHTMLRenderer


class JSONRendererWithESISupport(JSONRenderer):
    format = 'json'
    media_type = 'application/json'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        #  TODO: There should be a way to do this that is conditional on esi being requested and
        #  TODO: In such a way that it doesn't use regex unless there's absolutely no other way.
        initial_rendering = super(JSONRendererWithESISupport, self).render(data, accepted_media_type, renderer_context)
        augmented_rendering = re.sub(r'"<esi:include src=\\"(.*?)\\"\/>"', r'<esi:include src="\1"/>', initial_rendering)
        return augmented_rendering


class JSONAPIRenderer(JSONRendererWithESISupport):
    format = 'jsonapi'
    media_type = 'application/vnd.api+json'


class BrowsableAPIRendererNoForms(BrowsableAPIRenderer):
    """
    Renders browsable API but omits HTML forms
    """

    def get_context(self, *args, **kwargs):
        context = super(BrowsableAPIRendererNoForms, self).get_context(*args, **kwargs)
        unwanted_forms = ('put_form', 'post_form', 'delete_form', 'raw_data_put_form',
                          'raw_data_post_form', 'raw_data_patch_form', 'raw_data_put_or_patch_form')
        for form in unwanted_forms:
            del context[form]
        return context


class PlainTextRenderer(StaticHTMLRenderer):
    """
    Renders plain text.

    Inherits from StaticHTMLRenderer for error handling.
    """

    media_type = 'text/markdown'
    format = 'txt'
