from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.paginator import Paginator

from osf.models import (
    AbstractNode,
    Contributor,
    Preprint,
    PreprintContributor,
    DraftRegistration,
    DraftRegistrationContributor
)

from osf.models.spam import SpamStatus

register = template.Library()


@register.filter
def reverse_node(value):
    if hasattr(value, '_id'):
        return reverse('nodes:node', kwargs={'guid': value._id})
    else:
        return 'N/A'


@register.filter
def reverse_registration_schema(value):
    return reverse('registration_schemas:detail', kwargs={'registration_schema_id': value.id})


@register.filter
def reverse_preprint(value):
    return reverse('preprints:preprint', kwargs={'guid': value._id})


@register.filter
def reverse_user(user):
    return reverse('users:user', kwargs={'guid': user._id})


@register.filter
def reverse_osf_group(value):
    return reverse('osf_groups:osf_group', kwargs={'id': value._id})


@register.filter
def reverse_registration_provider(value):
    return reverse('registration_providers:detail', kwargs={'registration_provider_id': value.provider.id})


@register.filter
def reverse_preprint_provider(value):
    return reverse('preprint_providers:detail', kwargs={'preprint_provider_id': value.id})


@register.filter
def reverse_schema_response(value):
    return reverse('schema_responses:detail', kwargs={'schema_response_id': value.id})


@register.filter
def reverse_draft_registration(value):
    return reverse('draft_registrations:detail', kwargs={'draft_registration_id': value._id})


@register.filter
def order_by(queryset, args):
    args = [x.strip() for x in args.split(',')]
    return queryset.order_by(*args)


@register.simple_tag
def get_permissions(user, resource):
    if isinstance(resource, AbstractNode):
        return Contributor.objects.get(user=user, node=resource).permission
    elif isinstance(resource, Preprint):
        return PreprintContributor.objects.get(user=user, preprint=resource).permission
    elif isinstance(resource, DraftRegistration):
        return DraftRegistrationContributor.objects.get(user=user, draft_registration=resource).permission


@register.simple_tag
def get_spam_status(resource):
    if getattr(resource, 'is_assumed_ham', None):
        return mark_safe('<span class="label label-default">(assumed Ham)</span>')

    if resource.spam_status == SpamStatus.UNKNOWN:
        return mark_safe('<span class="label label-default">Unknown</span>')
    elif resource.spam_status == SpamStatus.FLAGGED:
        return mark_safe('<span class="label label-warning">Flagged</span>')
    elif resource.spam_status == SpamStatus.SPAM:
        return mark_safe('<span class="label label-danger">Spam</span>')
    elif resource.spam_status == SpamStatus.HAM:
        return mark_safe('<span class="label label-success">Ham</span>')

@register.simple_tag(takes_context=True)
def paginate(context, queryset, page_size):
    request = context['request']
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, page_size)
    return paginator.get_page(page)
