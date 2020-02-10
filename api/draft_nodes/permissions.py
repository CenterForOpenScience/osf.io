# -*- coding: utf-8 -*-
from osf.models import (
    DraftRegistration,
    DraftNode,
)
from api.nodes.permissions import ContributorOrPublic

from api.base.utils import assert_resource_type


class ContributorOnDraftRegistration(ContributorOrPublic):
    """
    DraftNodes are hidden entities - only used to store files for DraftRegistrations.
    Therefore, permission checking for DraftNodes will be done on the DraftRegistration.
    """

    acceptable_models = (DraftRegistration,)

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, DraftNode):
            obj = obj.registered_draft.first()
        assert_resource_type(obj, self.acceptable_models)
        return super(ContributorOnDraftRegistration, self).has_object_permission(request, view, obj)
