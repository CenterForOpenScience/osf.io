
from django.conf.urls import re_path

from api.preprint_providers import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.DeprecatedPreprintProviderList.as_view(), name=views.DeprecatedPreprintProviderList.view_name),
    re_path(r'^(?P<provider_id>\w+)/$', views.DeprecatedPreprintProviderDetail.as_view(), name=views.DeprecatedPreprintProviderDetail.view_name),
    re_path(r'^(?P<provider_id>\w+)/licenses/$', views.DeprecatedPreprintProviderLicenseList.as_view(), name=views.DeprecatedPreprintProviderLicenseList.view_name),
    re_path(r'^(?P<provider_id>\w+)/preprints/$', views.DeprecatedPreprintProviderPreprintList.as_view(), name=views.DeprecatedPreprintProviderPreprintList.view_name),
    re_path(r'^(?P<provider_id>\w+)/taxonomies/$', views.DeprecatedPreprintProviderTaxonomies.as_view(), name=views.DeprecatedPreprintProviderTaxonomies.view_name),
    re_path(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.DeprecatedPreprintProviderHighlightedSubjectList.as_view(), name=views.DeprecatedPreprintProviderHighlightedSubjectList.view_name),
    re_path(r'^(?P<provider_id>\w+)/moderators/$', views.DeprecatedPreprintProviderModeratorsList.as_view(), name=views.DeprecatedPreprintProviderModeratorsList.view_name),
    re_path(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.DeprecatedPreprintProviderModeratorsDetail.as_view(), name=views.DeprecatedPreprintProviderModeratorsDetail.view_name),
]
