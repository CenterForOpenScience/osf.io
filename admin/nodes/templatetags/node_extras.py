from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from osf.models import (
    AbstractNode,
    OSFUser,
    Registration,
    Contributor,
    Preprint,
    PreprintContributor
)

from osf.models.spam import SpamStatus

register = template.Library()


@register.filter
def reverse_node(value):
    if isinstance(value, (AbstractNode, Registration)):
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
def get_permissions(user_id, resource_id):
    if isinstance(resource_id, AbstractNode):
        return Contributor.objects.get(user_id=user_id, node_id=resource_id).permission
    elif isinstance(resource_id, Preprint):
        return PreprintContributor.objects.get(user_id=user_id, node_id=resource_id).permission


@register.simple_tag
def get_spam_status(resource):
    if getattr(resource, 'is_assumed_ham', None):
        return mark_safe('<span class="label label-default">(assumed Ham)</span>')

    print(resource)
    if resource.spam_status == SpamStatus.UNKNOWN:
        return mark_safe('<span class="label label-default">Unknown</span>')
    elif resource.spam_status == SpamStatus.FLAGGED:
        return mark_safe('<span class="label label-warning">Flagged</span>')
    elif resource.spam_status == SpamStatus.SPAM:
        return mark_safe('<span class="label label-danger">Spam</span>')
    elif resource.spam_status == SpamStatus.HAM:
        return mark_safe('<span class="label label-success">Ham</span>')
