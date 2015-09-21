
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer

class JSONAPIRenderer(JSONRenderer):
    format = "jsonapi"
    media_type = 'application/vnd.api+json'


class BrowsableAPIRendererNoForms(BrowsableAPIRenderer):
    """
    Renders browsable API but omits HTML forms
    """

    def get_context(self, *args, **kwargs):
        context = super(BrowsableAPIRendererNoForms, self).get_context(*args, **kwargs)
        del context['put_form']
        del context['post_form']
        return context
