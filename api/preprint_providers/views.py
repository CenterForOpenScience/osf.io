from api.base.views import DeprecatedView
from api.preprint_providers.serializers import DeprecatedPreprintProviderSerializer
from api.providers import views


class DeprecatedPreprintProviderList(DeprecatedView, views.PreprintProviderList):
    max_version = '2.7'
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'
    serializer_class = DeprecatedPreprintProviderSerializer

class DeprecatedPreprintProviderDetail(DeprecatedView, views.PreprintProviderDetail):
    max_version = '2.7'
    view_category = 'preprint_providers'
    view_name = 'preprint_providers-list'
    serializer_class = DeprecatedPreprintProviderSerializer

class DeprecatedPreprintProviderPreprintList(DeprecatedView, views.PreprintProviderPreprintList):
    view_category = 'preprint_providers'
    max_version = '2.7'

class DeprecatedPreprintProviderTaxonomies(DeprecatedView, views.PreprintProviderTaxonomies):
    view_category = 'preprint_providers'
    max_version = '2.7'

class DeprecatedPreprintProviderHighlightedSubjectList(DeprecatedView, views.PreprintProviderHighlightedSubjectList):
    view_category = 'preprint_providers'
    max_version = '2.7'

class DeprecatedPreprintProviderLicenseList(DeprecatedView, views.PreprintProviderLicenseList):
    view_category = 'preprint_providers'
    max_version = '2.7'

class DeprecatedPreprintProviderModeratorsList(DeprecatedView, views.PreprintProviderModeratorsList):
    max_version = '2.7'

class DeprecatedPreprintProviderModeratorsDetail(DeprecatedView, views.PreprintProviderModeratorsDetail):
    max_version = '2.7'
