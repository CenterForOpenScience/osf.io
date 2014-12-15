# OSF Google Drive Addon

# TODO


1. Copy settings/local-dist.py to settings/local.py and change the necessary settings.
...



# OSF Dropbox Addon

Enabling the addon for development

1. In `website/settings/local.py` add, `"gdrive"` to `ADDONS_REQUESTED`.
2. Create a local gdrive settings file with `cp website/addons/gdrive/settings/local-dist.py website/addons/gdrive/setings/local.py`
3. From https://console.developers.google.com, create a Project and navigate to Credentials page under APIs & Auth on the left.
4. Create a Client Id for Web Application
5. Add http://localhost:5000/api/v1/addons/gdrive/callback/ to your list of redirect URIs either while creating an application or by navigating to credentials page.
4. Enter your key and secret in `website/addons/gdrive/settings/local.py`. 
