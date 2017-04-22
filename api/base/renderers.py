import re

import yajl as yajl
from django.utils import six
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

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        if data is None:
            return bytes()

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context) or 4

        # if indent is None:
        #     separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        # else:
        #     separators = INDENT_SEPARATORS

        ret = yajl.dumps(  # YAJL is faster
            data,
            # , cls=self.encoder_class,
            # escape_forward_slashes=False,
            indent=indent,
            # ensure_ascii=self.ensure_ascii,
            # separators=separators
        )

        # On python 2.x json.dumps() returns bytestrings if ensure_ascii=True,
        # but if ensure_ascii=False, the return type is underspecified,
        # and may (or may not) be unicode.
        # On python 3.x json.dumps() returns unicode strings.
        if isinstance(ret, six.text_type):
            # We always fully escape \u2028 and \u2029 to ensure we output JSON
            # that is a strict javascript subset. If bytes were returned
            # by json.dumps() then we don't have these characters in any case.
            # See: http://timelessrepo.com/json-isnt-a-javascript-subset
            ret = ret.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
            return bytes(ret.encode('utf-8'))
        return ret


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
