# OSF Bitbucket Addon

## Enabling the addon for development

1. On your Bitbucket user settings, go to “OAuth Applications” -> "Developer applications" -> “Register new application”
2. Enter any name for the application name, e.g. "OSF Bitbucket Addon (local)"
3. In the Homepage URL field, enter "http://localhost:5000/“
4. In the Authorization Callback URL field, enter "http://localhost:5000/oauth/callback/bitbucket".
5. Submit the form.
6. cp website/addons/bitbucket/settings/defaults.py website/addons/bitbucket/settings/local.py
7. Copy your client ID and client secret from Bitbucket into the new local.py file.
8. Ensure `"bitbucket"` exists in the addons list in `"addons.json"`
9. Restart your app server.

## Testing webhooks

To test Bitbucket webhooks, your development server must be exposed to the web using a service like ngrok:
* brew install ngrok
* ngrok 5000
* Copy forwarding address to website/addons/bitbucket/settings/local.py:HOOK_DOMAIN
