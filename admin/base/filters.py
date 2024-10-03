from django import template
import json


register = template.Library()


@register.filter
def jsonify(o):
    return json.dumps(o)
