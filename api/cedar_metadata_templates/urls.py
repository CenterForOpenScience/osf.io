from django.urls import re_path

from api.cedar_metadata_templates import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.CedarMetadataTemplateList.as_view(), name=views.CedarMetadataTemplateList.view_name),
    re_path(r'^(?P<template_id>[0-9A-Za-z]+)/$', views.CedarMetadataTemplateDetail.as_view(), name=views.CedarMetadataTemplateDetail.view_name),
]
