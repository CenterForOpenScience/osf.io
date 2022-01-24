# GakuNin RDM OneDrive for Office365 Addon

## Enabling the addon for development

1. If `addons/onedrivebusiness/settings/local.py` does not yet exist, create a local onedrive settings file with `cp addons/onedrivebusiness/settings/local-dist.py addons/onedrivebusiness/settings/local.py`
2. Register the addon with Microsoft at https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade it should be a 'Web' platform and supported account types should be '**Accounts in any organizational directory (Any Azure AD directory - Multitenant)**'.
3. Enter the Redirect URL as http://localhost:5000/oauth/callback/onedrivebusiness/
4. Copy the value of the Application (client) ID and put that string as the `ONEDRIVE_KEY` in `addons/onedrivebusiness/settings/local.py`
5. Select Certificates & secrets under Manage. Select the New client secret button. Enter a value in Description and select one of the options for Expires and select Add.
6. Copy the client secret value before you leave this page and put that string as `ONEDRIVE_SECRET` in `addons/onedrivebusiness/settings/local.py`
