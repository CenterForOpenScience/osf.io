# OSF OneDrive Addon

Enabling the addon for development

1. In `website/settings/local.py` add, `"onedrive"` to the `ADDONS_REQUESTED` list.
2. If `website/addons/onedrive/settings/local.py` does not yet exist, create a local box settings file with `cp website/addons/onedrive/settings/local-dist.py website/addons/onedrive/settings/local.py`
...
?. Enter your Box `client_id` and `client_secret` as `BOX_KEY` and `BOX_SECRET` in `website/addons/box/settings/local.py`. 
