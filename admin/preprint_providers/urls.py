from django.conf.urls import url
from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.PreprintProviderList.as_view(), name='list'),
    url(r'^create/$', views.CreatePreprintProvider.as_view(), name='create'),
    url(r'^import/$', views.ImportPreprintProvider.as_view(), name='import'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/import/$', views.ImportPreprintProvider.as_view(), name='import'),
    url(r'^get_subjects/$', views.SubjectDynamicUpdateView.as_view(), name='get_subjects'),
    url(r'^get_descendants/$', views.GetSubjectDescendants.as_view(), name='get_descendants'),
    url(r'^process_custom_taxonomy/$', views.ProcessCustomTaxonomy.as_view(), name='process_custom_taxonomy'),
    url(r'^rules_to_subjects/$', views.RulesToSubjects.as_view(), name='rules_to_subjects'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/cannot_delete/$', views.CannotDeleteProvider.as_view(), name='cannot_delete'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/$', views.PreprintProviderDetail.as_view(), name='detail'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/delete/$', views.DeletePreprintProvider.as_view(), name='delete'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/export/$', views.ExportPreprintProvider.as_view(), name='export'),
]
