# OSF Google Drive Addon


Enabling the addon for development

1. In `website/settings/local.py` add, `"googledrive"` to `ADDONS_REQUESTED`.
2. Create a local googledrive settings file with `cp website/addons/googledrive/settings/local-dist.py website/addons/googledrive/settings/local.py`
3. From https://console.developers.google.com, create a Project and navigate to Credentials page under APIs & Auth on the left.
4. Create a Client Id for Web Application
5. Go to **APIs** underneath the **APIs & auth**.
  1. Search for **Drive API** in *Browse APIs*
  2. Click **Status** to turn the google drive API on.
6. Add http://localhost:5000/api/v1/addons/googledrive/callback/ to your list of redirect URIs either while creating an application or by navigating to credentials page.
7. Enter your key and secret in `website/addons/googledrive/settings/local.py`. 
