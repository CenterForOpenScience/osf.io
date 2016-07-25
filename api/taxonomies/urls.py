from django.conf.urls import url

from api.taxonomies import views

urlpatterns = [
    url(r'^flat$', views.TaxonomyFlat.as_view(), name=views.TaxonomyFlat.view_name),
    url(r'^treeview$', views.TaxonomyTreeview.as_view(), name=views.TaxonomyTreeview.view_name),
]
