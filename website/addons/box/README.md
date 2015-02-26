# OSF Box Addon

Enabling the addon for development

1. In `website/settings/local.py` add, `"box"` to `ADDONS_REQUESTED`.
2. Create a local box settings file with `cp website/addons/box/settings/local-dist.py website/addons/box/setings/local.py`
3. Create an app and get a key and secret from https://app.box.com/developers/services/edit/.
5. At the Box app console, add http://localhost:5000/api/v1/addons/box/oauth/finish/ to your list of Oauth2 redirect URIs.
4. Enter your key and secret in `website/addons/box/settings/local.py`. 
