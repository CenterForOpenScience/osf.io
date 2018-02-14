# OSF OneDrive Addon

Enabling the addon for development

1. If `addons/onedrive/settings/local.py` does not yet exist, create a local onedrive settings file with `cp addons/onedrive/settings/local-dist.py addons/onedrive/settings/local.py`
2. Register the addon with Microsoft at https://account.live.com/developers/applications/index it should be a 'Web' platform, not 'Web API'
3. Enter the Redirect URL as http://localhost:5000/oauth/callback/onedrive/
4. Click 'Generate New Password' and put that string as the `ONEDRIVE_SECRET` in `addons/onedrive/settings/local.py` and put the Application Id as `ONEDRIVE_KEY`
