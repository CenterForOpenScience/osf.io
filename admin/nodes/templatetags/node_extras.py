from django import template
from django.urls import reverse

from osf.models import Node, OSFUser

register = template.Library()


@register.filter
def reverse_node(value):
    if isinstance(value, Node):
        value = value._id
    return reverse('nodes:node', kwargs={'guid': value})

@register.filter
def reverse_preprint(value):
    return reverse('preprints:preprint', kwargs={'guid': value})

@register.filter
def reverse_user(user_id):
    if isinstance(user_id, int):
        user = OSFUser.objects.get(id=user_id)
    else:
        user = OSFUser.load(user_id)
    return reverse('users:user', kwargs={'guid': user._id})

@register.filter
def reverse_osf_group(value):
    return reverse('osf_groups:osf_group', kwargs={'id': value})
