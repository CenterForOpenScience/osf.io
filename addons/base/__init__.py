from django.db.models import options
default_app_config = 'addons.base.apps.BaseAddonAppConfig'


# Patch to make abstractproperties overridable by djangofields
if 'add_field' not in options.DEFAULT_NAMES:
    options.DEFAULT_NAMES += ('add_field', )
    original_add_field = options.Options.add_field

    def add_field_patched(self, field, **kwargs):
        prop = getattr(field.model, field.name, None)
        if prop and getattr(prop, '__isabstractmethod__', None):
            setattr(field.model, field.name, None)
        return original_add_field(field.model._meta, field, **kwargs)

    options.Options.add_field = add_field_patched
