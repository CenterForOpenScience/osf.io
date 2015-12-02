# OSF OneDrive Addon

Enabling the addon for development

1. In `website/settings/local.py` add, `"onedrive"` to the `ADDONS_REQUESTED` list.
2. If `website/addons/onedrive/settings/local.py` does not yet exist, create a local box settings file with `cp website/addons/onedrive/settings/local-dist.py website/addons/onedrive/settings/local.py`
3. Register the addon with Microsoft (https://account.live.com/developers/applications/index) and enter http://localhost:5000/oauth/callback/onedrive/ as the Redirect URL.
4. Enter your OneDrive `client_id` and `client_secret` as `ONEDRIVE_KEY` and `ONEDRIVE_SECRET` in `website/addons/onedrive/settings/local.py`. 
