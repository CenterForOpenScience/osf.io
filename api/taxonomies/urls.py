from django.conf.urls import url

from api.taxonomies import views


urlpatterns = [
    url(r'^plos/$', views.PlosTaxonomy.as_view(), name=views.PlosTaxonomy.view_name),
]
