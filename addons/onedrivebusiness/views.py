from boto import exception
from django.core.exceptions import ValidationError
from flask import request
from rest_framework import status as http_status

import addons.onedrivebusiness.settings as settings
from addons.base import generic_views
from addons.onedrivebusiness import SHORT_NAME, FULL_NAME
from addons.onedrivebusiness import utils
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer
from admin.rdm_addons.decorators import must_be_rdm_addons_allowed
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from osf.models import ExternalAccount
from website.project.decorators import (
    must_have_addon, must_have_permission,
    must_be_addon_authorizer,
)

onedrivebusiness_account_list = generic_views.account_list(
    SHORT_NAME,
    OneDriveBusinessSerializer
)

onedrivebusiness_get_config = generic_views.get_config(
    SHORT_NAME,
    OneDriveBusinessSerializer
)
