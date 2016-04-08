from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.filter
def reverse_node(value):
    return reverse('nodes:node', kwargs={'guid': value})
