from django import template

from admin.base.templatetags.base_extras import reverse_qs

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
    return reverse_qs('spam:user_spam', kwargs={'user_id': user_id},
                      query_kwargs=kwargs)


@register.simple_tag
def reverse_spam_email(spam_id, *args, **kwargs):
    return reverse_qs('spam:email', kwargs={'spam_id': spam_id},
                      query_kwargs=kwargs)
