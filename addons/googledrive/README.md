# OSF Google Drive Addon


## Enabling the addon for development



### Setup on Google APIs 
1. Go to https://console.developers.google.com
2. If you do not already have a project, create a project
3. Click on the "Google Drive API" link, and enable it
4. Click on "Credentials", and "create credentials". Select "Oath Client ID", with "web application" and set the redirect uri to `http://localhost:5000/oauth/callback/googledrive/`
5. Submit your new client ID and make a note of your new ID and secret

### Enable for OSF
1. Create a local googledrive settings file with `cp addons/googledrive/settings/local-dist.py addons/googledrive/settings/local.py`
2. Enter your key and secret in `addons/googledrive/settings/local.py`.
3. Ensure `"googledrive"` exists in the addons list in `"addons.json"`
4. Restart your server
5. Connect googledrive as a provider
6. Import and configure your new provider