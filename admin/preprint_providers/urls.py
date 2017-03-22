from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.PreprintProviderList.as_view(), name='list'),
    url(r'^create/$', views.CreatePreprintProvider.as_view(), name='create'),
    url(r'^import/$', views.ImportPreprintProvider.as_view(), name='import'),
    url(r'^rules_to_subjects/$', views.RulesToSubjects.as_view(), name='rules_to_subjects'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/$', views.PreprintProviderDetail.as_view(), name='detail'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/export/$', views.ExportPreprintProvider.as_view(), name='export'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/get_subjects/$', views.SubjectDynamicUpdateView.as_view(), name='get_subjects'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/process_subjects/$', views.ProcessSubjects.as_view(), name='process_subjects'),
    url(r'^(?P<preprint_provider_id>[a-z0-9]+)/get_children/$', views.GetSubjectDescendants.as_view(), name='get_descendants'),
]
