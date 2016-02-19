# -*- coding: utf-8 -*-
from website.project.decorators import (
    must_be_valid_project,
    must_have_permission,
    must_not_be_registration,
)
from website.util.permissions import ADMIN

from website.project.mailing_list import route_message


###############################################################################
# View Functions
###############################################################################


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def enable_discussions(node, **kwargs):
    node.mailing_enabled = True
    node.save()


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def disable_discussions(node, **kwargs):
    node.mailing_enabled = False
    node.save()

route_message = route_message
