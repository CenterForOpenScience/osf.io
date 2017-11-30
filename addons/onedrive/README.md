# OSF OneDrive Addon

Enabling the addon for development

1. If `addons/onedrive/settings/local.py` does not yet exist, create a local onedrive settings file with `cp addons/onedrive/settings/local-dist.py addons/onedrive/settings/local.py`
2. Register the addon with Microsoft (https://account.live.com/developers/applications/index) and enter http://localhost:5000/oauth/callback/onedrive/ as the Redirect URL.
3. Enter your OneDrive `client_id` and `client_secret` as `ONEDRIVE_KEY` and `ONEDRIVE_SECRET` in `addons/onedrive/settings/local.py`.
