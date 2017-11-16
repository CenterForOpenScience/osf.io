from django.conf.urls import url

from api.taxonomies import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.TaxonomyList.as_view(), name=views.TaxonomyList.view_name),
    url(r'^(?P<taxonomy_id>\w+)/$', views.TaxonomyDetail.as_view(), name=views.TaxonomyDetail.view_name),
]
