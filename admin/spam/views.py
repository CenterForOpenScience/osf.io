from django.shortcuts import render
from modularodm import Q

from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer

from website.models import Comment, Node


class SpamList(object):
    pass


def spam_detail(request, spam_id):
    render(request, None, )
