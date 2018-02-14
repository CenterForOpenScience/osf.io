# OSF Zotero Addon

## Enabling the addon for development

## Setup Zotero
1. Go to https://www.zotero.org/oauth/apps and create a new application
2. Enter any name for the application name, e.g. “OSF Zotero Addon (local)”
3. In the "Website" field, enter `http://localhost:5000/callback/`
4. In the Authorization Callback URL field, enter `http://localhost:5000/oauth/callback/zotero/`.
5. Submit the form. 
6. On the next page, make a note of your Client Key and Client Secret.

### Enable on OSF
1. If you do not have a local.py for zotero yet, run `cp addons/zotero/settings/defaults.py addons/zotero/settings/local.py`
2. Copy your client key and client secret from Zotero into the new local.py file.
3. Restart your app server.
