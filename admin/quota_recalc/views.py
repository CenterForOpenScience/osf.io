# from __future__ import unicode_literals

from django.http import HttpResponse

def by_user_id(request, **kwargs):
  return HttpResponse("Hello world!"+ " from user_id:"+ kwargs["user_id"])

def index(request, **kwargs):
  return HttpResponse("Hello world!")
