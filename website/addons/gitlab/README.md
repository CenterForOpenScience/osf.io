# OSF GitLab Addon

## Enabling the addon for development

1. On your GitLab profile settings, go to “Applications”
2. In the name field, enter your application name, e..g “OSF GitLab Addon (local)”
4. In the Redirect URI field, enter the full URL for your OSF instance + "/oauth/callback/gitlab", e.g "http://localhost:5000/oauth/callback/gitlab"
5. Click on 'Save application' button to submit the form.
6. cp website/addons/gitlab/settings/defaults.py website/addons/gitlab/settings/local.py
7. Copy your Application ID and Secret from GitLab into the new local.py file.
8. Restart your app server.

## Testing webhooks

To test GitLab webhooks, your development server must be exposed to the web using a service like ngrok:
* brew install ngrok
* ngrok 5000
* Copy forwarding address to website/addons/gitlab/settings/local.py:HOOK_DOMAIN
