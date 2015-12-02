from website.models import Institution, Node, User

from api.institutions.serializers import InstitutionSerializer, InstitutionDetailSerializer

from api.base.filters import ODMFilterMixin
from api.base.views import JSONAPIBaseView

class InstitutionList(JSONAPIBaseView, ODMFilterMixin):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Institution

    serializer_class = InstitutionSerializer
    view_category = 'institutions'
    view_name = 'institution-list'

    def get_default_odm_query(self):
        query = None
        return query


class InstitutionDetail(JSONAPIBaseView):
    permission_classes = ()

    required_read_scopes = []
    required_write_scopes = []
    model_class = Institution

    serializer_class = InstitutionDetailSerializer
    view_category = 'institutions'
    view_name = 'institution-detail'

class InstitutionNodeList():
    pass

class InstitutionNodeDetail():
    pass

class InstitutionUserList():
    pass

class InstituionUserDetail():
    pass
