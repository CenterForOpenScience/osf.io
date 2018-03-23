from api.base.views import DeprecatedView
from api.preprint_providers.serializers import DeprecatedPreprintProviderSerializer
from api.providers import views


class DeprecatedPreprintProviderList(DeprecatedView, views.PreprintProviderList):
    max_version = '2.7'
    serializer_class = DeprecatedPreprintProviderSerializer

class DeprecatedPreprintProviderDetail(DeprecatedView, views.PreprintProviderDetail):
    max_version = '2.7'
    serializer_class = DeprecatedPreprintProviderSerializer

class DeprecatedPreprintProviderPreprintList(DeprecatedView, views.PreprintProviderPreprintList):
    max_version = '2.7'

class DeprecatedPreprintProviderTaxonomies(DeprecatedView, views.PreprintProviderTaxonomies):
    max_version = '2.7'

class DeprecatedPreprintProviderHighlightedSubjectList(DeprecatedView, views.PreprintProviderHighlightedSubjectList):
    max_version = '2.7'

class DeprecatedPreprintProviderLicenseList(DeprecatedView, views.PreprintProviderLicenseList):
    max_version = '2.7'

class DeprecatedPreprintProviderModeratorsList(DeprecatedView, views.PreprintProviderModeratorsList):
    max_version = '2.7'

class DeprecatedPreprintProviderModeratorsDetail(DeprecatedView, views.PreprintProviderModeratorsDetail):
    max_version = '2.7'
