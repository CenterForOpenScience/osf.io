from django.urls import re_path
from . import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.PreprintProviderList.as_view(), name='list'),
    re_path(r'^create/$', views.CreatePreprintProvider.as_view(), name='create'),
    re_path(r'^import/$', views.ImportPreprintProvider.as_view(), name='import'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/import/$', views.ImportPreprintProvider.as_view(), name='import'),
    re_path(r'^get_subjects/$', views.SubjectDynamicUpdateView.as_view(), name='get_subjects'),
    re_path(r'^get_descendants/$', views.GetSubjectDescendants.as_view(), name='get_descendants'),
    re_path(r'^rules_to_subjects/$', views.RulesToSubjects.as_view(), name='rules_to_subjects'),
    re_path(r'^whitelist/$', views.SharePreprintProviderWhitelist.as_view(), name='whitelist'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/process_custom_taxonomy/$', views.ProcessCustomTaxonomy.as_view(), name='process_custom_taxonomy'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/$', views.PreprintProviderDetail.as_view(), name='detail'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/delete/$', views.DeletePreprintProvider.as_view(), name='delete'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/export/$', views.ExportPreprintProvider.as_view(), name='export'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/share_source/$', views.ShareSourcePreprintProvider.as_view(), name='share_source'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/register/$', views.PreprintProviderRegisterModeratorOrAdmin.as_view(), name='register_moderator_admin'),
    re_path(r'^(?P<preprint_provider_id>[a-z0-9]+)/edit/$', views.PreprintProviderChangeForm.as_view(), name='edit'),
]
