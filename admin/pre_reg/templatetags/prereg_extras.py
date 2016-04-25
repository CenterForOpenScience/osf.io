from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def reverse_list(*args, **kwargs):
    return '{}?page={}&status={}&order_by={}&p={}'.format(
        reverse('pre_reg:prereg'),
        kwargs.get('page', 1),
        kwargs.get('status', 1),
        kwargs.get('order_by', ''),
        kwargs.get('p', 10)
    )
