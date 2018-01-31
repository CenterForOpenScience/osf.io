import django_filters

from osf.models import OSFUser
from api.base.filters import JSONAPIFilterSet, MultiValueCharFilter


class UserFilterSet(JSONAPIFilterSet):

    full_name = MultiValueCharFilter(name='fullname', lookup_expr='icontains')
    id = django_filters.CharFilter(name='guids___id')

    class Meta(JSONAPIFilterSet.Meta):
        model = OSFUser
        fields = ['id', 'full_name', 'given_name', 'middle_names', 'family_name']
