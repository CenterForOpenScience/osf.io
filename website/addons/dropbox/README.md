# OSF Dropbox Addon

Enabling the addon

1. In `website/settings/local.py` add, `"dropbox"` to `ADDONS_REQUESTED`.
2. Create a local dropbox settings file with `cp website/addons/dropbox/settings/local-dist.py website/addons/dropbox/setings/local.py`
3. Create an app and get a key and secret from https://www.dropbox.com/developers/apps.
4. Enter your key and secret in `website/addons/dropbox/settings/local.py`. 
