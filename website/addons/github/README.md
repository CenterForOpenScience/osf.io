# OSF Github Addon

## Enabling the addon for development

1. On your Github user settings, go to “OAuth Applications” -> "Developer applications" -> “Register new application”
2. Enter any name for the application name, e..g “OSF Github Addon (local)”
3. In the Homepage URL field, enter "http://localhost:5000/“
4. In the Authorization Callback URL field, enter "http://localhost:5000/oauth/callback/github".
5. Submit the form.
6. cp website/addons/github/settings/defaults.py website/addons/github/settings/local.py
7. Copy your client ID and client secret from Github into the new local.py file.
8. Restart your app server.

## Testing webhooks

To test Github webhooks, your development server must be exposed to the web using a service like ngrok:
* brew install ngrok
* ngrok 5000
* Copy forwarding address to website/addons/github/settings/local.py:HOOK_DOMAIN

