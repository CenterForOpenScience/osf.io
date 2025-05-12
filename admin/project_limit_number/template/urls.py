from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.ProjectLimitNumberTemplateListView.as_view(), name='list-template'),
    url(r'^create/$', views.ProjectLimitNumberTemplatesViewCreate.as_view(), name='create-template'),
    url(r'^update/$', views.ProjectLimitNumberTemplatesSettingSaveAvailabilityView.as_view(), name='save-templates-availability'),
    url(r'^(?P<template_id>[0-9]+)/$', views.ProjectLimitNumberTemplatesViewUpdate.as_view(), name='detail-template'),
    url(r'^(?P<template_id>[0-9]+)/update/$', views.UpdateProjectLimitNumberTemplatesSettingView.as_view(), name='update-template'),
    url(r'^delete/(?P<template_id>[0-9]+)/$', views.DeleteProjectLimitNumberTemplatesSettingView.as_view(), name='delete-template'),
]
