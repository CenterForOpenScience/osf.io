
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
        unwanted_forms = ('put_form', 'post_form', 'delete_form', 'raw_data_put_form',
                          'raw_data_post_form', 'raw_data_patch_form', 'raw_data_put_or_patch_form')
        for form in unwanted_forms:
            del context[form]
        return context
