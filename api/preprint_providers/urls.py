from django.urls import re_path
from api.preprint_providers import views

app_name = 'osf'

# URL configurations for the OSF app related to preprint providers.
# Each URL pattern corresponds to an API view that handles specific operations
# related to preprint providers.

urlpatterns = [
    # List all preprint providers.
    # Note: This endpoint is deprecated.
    re_path(r'^$', views.DeprecatedPreprintProviderList.as_view(), name=views.DeprecatedPreprintProviderList.view_name),

    # Detail view for a specific preprint provider based on its ID.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/$', views.DeprecatedPreprintProviderDetail.as_view(), name=views.DeprecatedPreprintProviderDetail.view_name),

    # List licenses associated with a specific preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/licenses/$', views.DeprecatedPreprintProviderLicenseList.as_view(), name=views.DeprecatedPreprintProviderLicenseList.view_name),

    # List preprints associated with a specific preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/preprints/$', views.DeprecatedPreprintProviderPreprintList.as_view(), name=views.DeprecatedPreprintProviderPreprintList.view_name),

    # List taxonomies (subjects or categories) for a specific preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/taxonomies/$', views.DeprecatedPreprintProviderTaxonomies.as_view(), name=views.DeprecatedPreprintProviderTaxonomies.view_name),

    # List highlighted subjects for a specific preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/taxonomies/highlighted/$', views.DeprecatedPreprintProviderHighlightedSubjectList.as_view(), name=views.DeprecatedPreprintProviderHighlightedSubjectList.view_name),

    # List moderators for a specific preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/moderators/$', views.DeprecatedPreprintProviderModeratorsList.as_view(), name=views.DeprecatedPreprintProviderModeratorsList.view_name),

    # Detail view for a specific moderator of a preprint provider.
    # Note: This endpoint is deprecated.
    re_path(r'^(?P<provider_id>\w+)/moderators/(?P<moderator_id>\w+)/$', views.DeprecatedPreprintProviderModeratorsDetail.as_view(), name=views.DeprecatedPreprintProviderModeratorsDetail.view_name),
]
