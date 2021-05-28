# OSF OneDrive Addon

Enabling the addon for development

1. If `addons/onedrive/settings/local.py` does not yet exist, create a local onedrive settings file with `cp addons/onedrive/settings/local-dist.py addons/onedrive/settings/local.py`
2. Register the addon with Microsoft at https://aad.portal.azure.com/#blade/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps it should be a 'Web' platform
3. Enter the Redirect URL as http://localhost:5000/oauth/callback/onedrive/
4. Copy the value of the Application (client) ID and put that string as the `ONEDRIVE_KEY` in `addons/onedrive/settings/local.py`
5. Select Certificates & secrets under Manage. Select the New client secret button. Enter a value in Description and select one of the options for Expires and select Add.
6. Copy the client secret value before you leave this page and put that string as `ONEDRIVE_SECRET` in `addons/onedrive/settings/local.py`

See also https://docs.microsoft.com/en-us/graph/tutorials/python?tutorial-step=2
