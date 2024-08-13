from django.urls import re_path

from api.taxonomies import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.TaxonomyList.as_view(), name=views.TaxonomyList.view_name),
    re_path(r'^(?P<taxonomy_id>\w+)/$', views.TaxonomyDetail.as_view(), name=views.TaxonomyDetail.view_name),
]
