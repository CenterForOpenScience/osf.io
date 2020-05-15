# h/t https://djangosnippets.org/snippets/1250/
from django import template
from django.utils.safestring import mark_safe
import json
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.filter
def jsonify(o):
    return mark_safe(json.dumps(o))

@register.filter
def transValue(value1):
    return _(str(value1))
