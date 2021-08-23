from django import template
from django.urls import reverse

register = template.Library()


@register.filter
def reverse_user(value):
    return reverse('users:user', kwargs={'guid': value})
