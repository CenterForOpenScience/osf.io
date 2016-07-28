from django.conf.urls import url

from api.taxonomies import views

urlpatterns = [
    url(r'^plos/flat/$', views.PlosTaxonomyFlat.as_view(), name=views.PlosTaxonomyFlat.view_name),
    url(r'^plos/treeview/$', views.PlosTaxonomyTreeview.as_view(), name=views.PlosTaxonomyTreeview.view_name),
]
