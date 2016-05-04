from django import template

from admin.base.utils import reverse_qs

register = template.Library()


@register.simple_tag
def reverse_list(*args, **kwargs):
    return reverse_qs('pre_reg:prereg', query_kwargs=kwargs)
