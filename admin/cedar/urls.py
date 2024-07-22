from django.urls import re_path

from admin.cedar import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.CedarMetadataTemplateListView.as_view(), name='list'),
    re_path(r'^(?P<id>[0-9_]+)/$', views.CedarMetadataTemplateDetailView.as_view(),
        name='detail'),
]
