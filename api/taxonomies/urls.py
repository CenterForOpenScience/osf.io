from django.conf.urls import url

from api.taxonomies import views

urlpatterns = [
    url(r'^$', views.Taxonomy.as_view(), name=views.Taxonomy.view_name),
]
