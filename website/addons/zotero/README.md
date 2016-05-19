# OSF Zotero Addon

## Enabling the addon for development

1. Go to https://www.zotero.org/oauth/apps and create a new application
2. Enter any name for the application name, e.g. “OSF Zotero Addon (local)”
3. In the Website field, enter "http://localhost:5000/callback/“
4. In the Authorization Callback URL field, enter "http://localhost:5000/oauth/callback/zotero/".
5. Submit the form.
6. cp website/addons/zotero/settings/defaults.py website/addons/zotero/settings/local.py
7. Copy your client key and client secret from Zotero into the new local.py file.
8. Restart your app server.
