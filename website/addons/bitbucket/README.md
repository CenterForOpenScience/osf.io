# OSF Bitbucket Addon

## Enabling the addon for development

1. On your Bitbucket user settings, go to "Access Management" -> "OAuth" -> "Add OAuth consumer"/
2. Enter any name for the application name, e.g. "OSF Bitbucket Addon (local)"
3. In the Callback URL field, enter "http://localhost:5000/oauth/callback/bitbucket"
4. In the URL field, enter "http://localhost:5000/"
5. For Permissions, select:
 * Account: Email, Read
 * Projects: Read
 * Repositories: Read
5. Submit the form.
6. `cp website/addons/bitbucket/settings/local-dist.py website/addons/bitbucket/settings/local.py`
7. Copy your new application's Key and Secret from Bitbucket into the new `local.py` file.
8. Ensure `"bitbucket"` exists in the addons list in `"addons.json"`
9. Restart your app server.

## Testing webhooks

To test Bitbucket webhooks, your development server must be exposed to the web using a service like ngrok:
* brew install ngrok
* ngrok 5000
* Copy forwarding address to website/addons/bitbucket/settings/local.py:HOOK_DOMAIN
