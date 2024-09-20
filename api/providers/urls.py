from django.conf.urls import include
from django.urls import re_path
from api.providers import views
from api.subscriptions.views import (
    PreprintProviderSubscriptionDetail,
    RegistrationProviderSubscriptionDetail,
    CollectionProviderSubscriptionDetail,
    PreprintProviderSubscriptionList,
    RegistrationProviderSubscriptionList,
    CollectionProviderSubscriptionList,
)

app_name = 'osf'

urlpatterns = [
    re_path(
        r'^preprints/', include(
            (
                [
                    re_path(r'^$', views.PreprintProviderList.as_view(), name=views.PreprintProviderList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/$', views.PreprintProviderDetail.as_view(), name=views.PreprintProviderDetail.view_name),
                    re_path(r'^(?P<provider_id>\w+)/licenses/$', views.PreprintProviderLicenseList.as_view(), name=views.PreprintProviderLicenseList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/preprints/$', views.PreprintProviderPreprintList.as_view(), name=views.PreprintProviderPreprintList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/$', views.PreprintProviderSubjects.as_view(), name=views.PreprintProviderSubjects.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/highlighted/$', views.PreprintProviderHighlightedSubjectList.as_view(), name=views.PreprintProviderHighlightedSubjectList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/$', views.PreprintProviderTaxonomies.as_view(), name=views.PreprintProviderTaxonomies.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.PreprintProviderHighlightedTaxonomyList.as_view(), name=views.PreprintProviderHighlightedTaxonomyList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/withdraw_requests/$', views.PreprintProviderWithdrawRequestList.as_view(), name=views.PreprintProviderWithdrawRequestList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/$', views.PreprintProviderModeratorsList.as_view(), name=views.PreprintProviderModeratorsList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.PreprintProviderModeratorsDetail.as_view(), name=views.PreprintProviderModeratorsDetail.view_name),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/(?P<subscription_id>\w+)/$',
                        PreprintProviderSubscriptionDetail.as_view(),
                        name=PreprintProviderSubscriptionDetail.view_name,
                    ),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/$',
                        PreprintProviderSubscriptionList.as_view(),
                        name=PreprintProviderSubscriptionList.view_name,
                    ),
                    # Retrieve citation styles associated with a specific preprint provider.
                    re_path(
                        r'^(?P<provider_id>\w+)/citation_styles/$',
                        views.PreprintProviderCitationStylesView.as_view(),
                        name=views.PreprintProviderCitationStylesView.view_name,
                    ),
                ], 'preprints',
            ),
            namespace='preprint-providers',
        ),
    ),

    re_path(
        r'^collections/', include(
            (
                [
                    re_path(r'^$', views.CollectionProviderList.as_view(), name=views.CollectionProviderList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/$', views.CollectionProviderDetail.as_view(), name=views.CollectionProviderDetail.view_name),
                    re_path(r'^(?P<provider_id>\w+)/licenses/$', views.CollectionProviderLicenseList.as_view(), name=views.CollectionProviderLicenseList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/submissions/$', views.CollectionProviderSubmissionList.as_view(), name=views.CollectionProviderSubmissionList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/$', views.CollectionProviderSubjects.as_view(), name=views.CollectionProviderSubjects.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/highlighted/$', views.CollectionProviderHighlightedSubjectList.as_view(), name=views.CollectionProviderHighlightedSubjectList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/$', views.CollectionProviderTaxonomies.as_view(), name=views.CollectionProviderTaxonomies.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.CollectionProviderHighlightedTaxonomyList.as_view(), name=views.CollectionProviderHighlightedTaxonomyList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/$', views.CollectionProviderModeratorsList.as_view(), name=views.CollectionProviderModeratorsList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.CollectionProviderModeratorsDetail.as_view(), name=views.CollectionProviderModeratorsDetail.view_name),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/(?P<subscription_id>\w+)/$',
                        CollectionProviderSubscriptionDetail.as_view(),
                        name=CollectionProviderSubscriptionDetail.view_name,
                    ),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/$',
                        CollectionProviderSubscriptionList.as_view(),
                        name=CollectionProviderSubscriptionList.view_name,
                    ),
                ], 'collections',
            ),
            namespace='collection-providers',
        ),
    ),

    re_path(
        r'^registrations/', include(
            (
                [
                    re_path(r'^$', views.RegistrationProviderList.as_view(), name=views.RegistrationProviderList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/$', views.RegistrationProviderDetail.as_view(), name=views.RegistrationProviderDetail.view_name),
                    re_path(r'^(?P<provider_id>\w+)/licenses/$', views.RegistrationProviderLicenseList.as_view(), name=views.RegistrationProviderLicenseList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/schemas/$', views.RegistrationProviderSchemaList.as_view(), name=views.RegistrationProviderSchemaList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/submissions/$', views.RegistrationProviderSubmissionList.as_view(), name=views.RegistrationProviderSubmissionList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/$', views.RegistrationProviderSubjects.as_view(), name=views.RegistrationProviderSubjects.view_name),
                    re_path(r'^(?P<provider_id>\w+)/subjects/highlighted/$', views.RegistrationProviderHighlightedSubjectList.as_view(), name=views.RegistrationProviderHighlightedSubjectList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/$', views.RegistrationProviderTaxonomies.as_view(), name=views.RegistrationProviderTaxonomies.view_name),
                    re_path(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.RegistrationProviderHighlightedTaxonomyList.as_view(), name=views.RegistrationProviderHighlightedTaxonomyList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/requests/$', views.RegistrationProviderRequestList.as_view(), name=views.RegistrationProviderRequestList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/registrations/$', views.RegistrationProviderRegistrationList.as_view(), name=views.RegistrationProviderRegistrationList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/actions/$', views.RegistrationProviderActionList.as_view(), name=views.RegistrationProviderActionList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/$', views.RegistrationProviderModeratorsList.as_view(), name=views.RegistrationProviderModeratorsList.view_name),
                    re_path(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.RegistrationProviderModeratorsDetail.as_view(), name=views.RegistrationProviderModeratorsDetail.view_name),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/(?P<subscription_id>\w+)/$',
                        RegistrationProviderSubscriptionDetail.as_view(),
                        name=RegistrationProviderSubscriptionDetail.view_name,
                    ),
                    re_path(
                        r'^(?P<provider_id>\w+)/subscriptions/$',
                        RegistrationProviderSubscriptionList.as_view(),
                        name=RegistrationProviderSubscriptionList.view_name,
                    ),
                ],
                'registrations',
            ),
            namespace='registration-providers',
        ),
    ),
]
