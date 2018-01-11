from itertools import chain
from waffle.models import Flag, Switch, Sample

from rest_framework import generics
from rest_framework import permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.permissions import TokenHasScope
from api.waffle.serializers import WaffleSerializer
from framework.auth.oauth_scopes import CoreScopes


class WaffleList(JSONAPIBaseView, generics.ListAPIView):
    """List of waffle switches, samples, and flags for use in feature flipping.

    This is a nonstandard, heterogeneous endpoint that you can filter against to fetch
    more than one flag, switch, or sample in a single request.

    This is an example of how to query against the _waffle endpoint:
    ``/v2/_waffle/?samples=test_sample&flags=test_flag,second_flag`

    ##Waffle Attributes

    Waffle entities have the "waffle" `type`.

        name               type               description
        ========================================================================================
        id                 string             <flag/switch/sample>_<resource_id>
        name               string             The human/computer readable name of the flag/sample/switch.
        note               string             Description of where flag/sample/switch is used or other details
        active             boolean            Whether the flag/sample/switch is active for the logged-in user

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1
    + `flags=<>` -- comma-separated list of flag names
    + `switches=<>` -- comma-separated list of switch names
    + `samples=<>` -- comman-separated list of sample names

    #This Request/Response

    """
    permission_classes = (
        TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.WAFFLE_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = WaffleSerializer
    view_category = 'waffle'
    view_name = 'waffle-list'

    # overrides ListAPIView
    def get_queryset(self):
        query_params = self.request.query_params
        if query_params:
            flags = Flag.objects.filter(name__in=query_params['flags'].split(',')) if 'flags' in query_params else []
            switches = Switch.objects.filter(name__in=query_params['switches'].split(',')) if 'switches' in query_params else []
            samples = Sample.objects.filter(name__in=query_params['samples'].split(',')) if 'samples' in query_params else []
            return list(chain(flags, switches, samples))
        else:
            return list(chain(Flag.objects.all(), Switch.objects.all(), Sample.objects.all()))
