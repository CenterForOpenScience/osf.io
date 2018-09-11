from django.conf.urls import include, url

from api.providers import views

app_name = 'osf'

urlpatterns = [
    url(r'^preprints/', include([
        url(r'^$', views.PreprintProviderList.as_view(), name=views.PreprintProviderList.view_name),
        url(r'^(?P<provider_id>\w+)/$', views.PreprintProviderDetail.as_view(), name=views.PreprintProviderDetail.view_name),
        url(r'^(?P<provider_id>\w+)/licenses/$', views.PreprintProviderLicenseList.as_view(), name=views.PreprintProviderLicenseList.view_name),
        url(r'^(?P<provider_id>\w+)/preprints/$', views.PreprintProviderPreprintList.as_view(), name=views.PreprintProviderPreprintList.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/$', views.PreprintProviderTaxonomies.as_view(), name=views.PreprintProviderTaxonomies.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.PreprintProviderHighlightedSubjectList.as_view(), name=views.PreprintProviderHighlightedSubjectList.view_name),
        url(r'^(?P<provider_id>\w+)/withdraw_requests/$', views.PreprintProviderWithdrawRequestList.as_view(), name=views.PreprintProviderWithdrawRequestList.view_name),
        url(r'^(?P<provider_id>\w+)/moderators/$', views.PreprintProviderModeratorsList.as_view(), name=views.PreprintProviderModeratorsList.view_name),
        url(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.PreprintProviderModeratorsDetail.as_view(), name=views.PreprintProviderModeratorsDetail.view_name),
    ], namespace='preprint-providers')),

    url(r'^collections/', include([
        url(r'^$', views.CollectionProviderList.as_view(), name=views.CollectionProviderList.view_name),
        url(r'^(?P<provider_id>\w+)/$', views.CollectionProviderDetail.as_view(), name=views.CollectionProviderDetail.view_name),
        url(r'^(?P<provider_id>\w+)/licenses/$', views.CollectionProviderLicenseList.as_view(), name=views.CollectionProviderLicenseList.view_name),
        url(r'^(?P<provider_id>\w+)/submissions/$', views.CollectionProviderSubmissionList.as_view(), name=views.CollectionProviderSubmissionList.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/$', views.CollectionProviderTaxonomies.as_view(), name=views.CollectionProviderTaxonomies.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.CollectionProviderHighlightedSubjectList.as_view(), name=views.CollectionProviderHighlightedSubjectList.view_name),
    ], namespace='collection-providers')),

    url(r'^registrations/', include([
        url(r'^$', views.RegistrationProviderList.as_view(), name=views.RegistrationProviderList.view_name),
        url(r'^(?P<provider_id>\w+)/$', views.RegistrationProviderDetail.as_view(), name=views.RegistrationProviderDetail.view_name),
        url(r'^(?P<provider_id>\w+)/licenses/$', views.RegistrationProviderLicenseList.as_view(), name=views.RegistrationProviderLicenseList.view_name),
        url(r'^(?P<provider_id>\w+)/submissions/$', views.RegistrationProviderSubmissionList.as_view(), name=views.RegistrationProviderSubmissionList.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/$', views.RegistrationProviderTaxonomies.as_view(), name=views.RegistrationProviderTaxonomies.view_name),
        url(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.RegistrationProviderHighlightedSubjectList.as_view(), name=views.RegistrationProviderHighlightedSubjectList.view_name),
    ], namespace='registration-providers')),

]
