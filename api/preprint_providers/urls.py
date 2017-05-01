
from django.conf.urls import url

from api.preprint_providers import views

urlpatterns = [
    url(r'^$', views.PreprintProviderList.as_view(), name=views.PreprintProviderList.view_name),
    url(r'^(?P<provider_id>\w+)/$', views.PreprintProviderDetail.as_view(), name=views.PreprintProviderDetail.view_name),
    url(r'^(?P<provider_id>\w+)/licenses/$', views.PreprintProviderLicenseList.as_view(), name=views.PreprintProviderLicenseList.view_name),
    url(r'^(?P<provider_id>\w+)/preprints/$', views.PreprintProviderPreprintList.as_view(), name=views.PreprintProviderPreprintList.view_name),
    url(r'^(?P<provider_id>\w+)/taxonomies/$', views.PreprintProviderSubjectList.as_view(), name=views.PreprintProviderSubjectList.view_name),
]
