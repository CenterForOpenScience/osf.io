from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.InstitutionListView.as_view(), name='list'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', views.InstitutionDetailView.as_view(),
        name='detail'),
    url(r'^form/$', views.InstitutionFormView.as_view(), name='form')
]
