from django import template

from admin.base.utils import reverse_qs

register = template.Library()


@register.simple_tag
def reverse_spam_detail(spam_id, *args, **kwargs):
    return reverse_qs('spam:detail', kwargs={'spam_id': spam_id},
                      query_kwargs=kwargs)


@register.simple_tag
def reverse_spam_list(*args, **kwargs):
    return reverse_qs('spam:spam', query_kwargs=kwargs)


@register.simple_tag
def reverse_spam_user(user_id, *args, **kwargs):
    return reverse_qs(
        'spam:user_spam',
        kwargs={'guid': user_id},
        query_kwargs=kwargs
    )
