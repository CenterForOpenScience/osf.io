# OSF Dropbox Addon

Enabling the addon for development

1. Create a local dropbox settings file with `cp addons/dropbox/settings/local-dist.py addons/dropbox/setings/local.py`
2. Create an app and get a key and secret from https://www.dropbox.com/developers/apps.
3. At the Dropbox app console, add http://localhost:5000/oauth/callback/dropbox/ to your list of Oauth2 redirect URIs.
4. Enter your key and secret in `addons/dropbox/settings/local.py`.
5. Ensure `"dropbox"` exists in the addons list in `"addons.json"`
