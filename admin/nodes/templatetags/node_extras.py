from django import template
from django.urls import reverse

from osf.models import Node, OSFUser, Registration, Contributor

register = template.Library()


@register.filter
def reverse_node(value):
    if isinstance(value, (Node, Registration)):
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


@register.filter
def reverse_registration_provider(value):
    return reverse('registration_providers:detail', kwargs={'registration_provider_id': value})


@register.filter
def reverse_schema_response(value):
    return reverse('schema_responses:detail', kwargs={'schema_response_id': value})


@register.filter
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)


@register.simple_tag
def get_permissions(user_id, node_id):
    return Contributor.objects.get(user_id=user_id, node_id=node_id).permission

