from api.base.views import DeprecatedView
from api.schemas import views
from api.schemas.serializers import DeprecatedMetaSchemaSerializer


class DeprecatedRegistrationMetaSchemaList(DeprecatedView, views.RegistrationSchemaList):
    max_version = '2.8'
    view_category = 'registration-metaschemas'
    view_name = 'registration-schema-detail'


class DeprecatedRegistrationMetaSchemaDetail(DeprecatedView, views.RegistrationSchemaDetail):
    max_version = '2.8'
    view_category = 'registration-metaschemas'
    view_name = 'registration-schema-detail'


class DeprecatedMetaSchemasList(DeprecatedView, views.RegistrationSchemaList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_list).
    """
    max_version = '2.7'
    view_category = 'metaschemas'
    view_name = 'metaschema-list'
    serializer_class = DeprecatedMetaSchemaSerializer


class DeprecatedMetaSchemaDetail(DeprecatedView, views.RegistrationSchemaDetail):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/metaschemas_read).
    """
    max_version = '2.7'
    view_category = 'metaschemas'
    view_name = 'metaschema-detail'
    serializer_class = DeprecatedMetaSchemaSerializer
