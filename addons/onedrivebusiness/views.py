from addons.base import generic_views
from addons.onedrivebusiness import SHORT_NAME
from addons.onedrivebusiness.serializer import OneDriveBusinessSerializer

onedrivebusiness_account_list = generic_views.account_list(
    SHORT_NAME,
    OneDriveBusinessSerializer
)

onedrivebusiness_get_config = generic_views.get_config(
    SHORT_NAME,
    OneDriveBusinessSerializer
)
