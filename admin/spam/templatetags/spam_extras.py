from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def reverse_spam_detail(spam_id, *args, **kwargs):
    page = kwargs.get('page', 1)
    status = kwargs.get('status', 1)
    return '{}?page={}&status={}'.format(
        reverse('spam:detail', kwargs={'spam_id': spam_id}),
        page, status
    )


@register.simple_tag
def reverse_spam_list(*args, **kwargs):
    page = kwargs.get('page', 1)
    status = kwargs.get('status', 1)
    return '{}?page={}&status={}'.format(
        reverse('spam:spam'),
        page, status
    )


@register.simple_tag
def reverse_spam_user(user_id, *args, **kwargs):
    page = kwargs.get('page', 1)
    status = kwargs.get('status', 1)
    return '{}?page={}&status={}'.format(
        reverse('spam:user_spam', kwargs={'user_id': user_id}),
        page, status
    )


@register.simple_tag
def reverse_spam_email(spam_id, *args, **kwargs):
    page = kwargs.get('page', 1)
    status = kwargs.get('status', 1)
    return '{}?page={}&status={}'.format(
        reverse('spam:email', kwargs={'spam_id': spam_id}),
        page, status
    )
