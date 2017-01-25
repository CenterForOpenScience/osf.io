# OSF Google Drive Addon


Enabling the addon for development

1. Create a local googledrive settings file with `cp website/addons/googledrive/settings/local-dist.py website/addons/googledrive/settings/local.py`
2. From https://console.developers.google.com, create a Project and navigate to Credentials page under APIs & Auth on the left.
3. Create a Client Id for Web Application
4. Go to **APIs** underneath the **APIs & auth**.
  1. Search for **Drive API** in *Browse APIs*
  2. Click **Status** to turn the google drive API on.
5. Add http://localhost:5000/oauth/callback/googledrive/ to your list of redirect URIs either while creating an application or by navigating to credentials page.
6. Enter your key and secret in `website/addons/googledrive/settings/local.py`. 
7. Ensure `"googledrive"` exists in the addons list in `"addons.json"`
