from django import template
from django.utils.safestring import mark_safe
from django.utils import simplejson

register = template.Library()

@register.filter('jsonify')
def jsonify(o):
    return mark_safe(simplejson.dumps(o))
