# OSF Mendeley Addon

## Enabling the addon for development

1. Go to http://dev.mendeley.com/myapps.html and register a new application
2. Enter any name for the application name, e.g. “OSF Mendeley Addon (local)”
3. Enter anything for the application description.
4. In the Redirect URL field, enter "http://localhost:5000/oauth/callback/mendeley/".
5. Submit the form.
6. cp website/addons/mendeley/settings/defaults.py website/addons/mendeley/settings/local.py
7. Copy your client ID and client secret from Mendeley into the new local.py file.
8. Restart your app server.
