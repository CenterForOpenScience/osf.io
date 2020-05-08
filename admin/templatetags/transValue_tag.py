from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.filter
def transValue(value1):
    return _(value1)