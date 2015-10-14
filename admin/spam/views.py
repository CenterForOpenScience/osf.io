from django.shortcuts import render
from modularodm import Q

from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer

from website.models import Comment, Node

from django.http import HttpResponse


def spam_list(request):
    return HttpResponse('This is a list of spam')


# class SpamList(object):
#     pass


def spam_detail(request, spam_id):
    return HttpResponse('Looking at spam {}'.format(spam_id))
