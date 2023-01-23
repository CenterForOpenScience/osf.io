# OSF OneDrive Addon

Enabling the addon for development

1. If `addons/onedrive/settings/local.py` does not yet exist, create a local onedrive settings file with `cp addons/onedrive/settings/local-dist.py addons/onedrive/settings/local.py`
2. Register the addon with Microsoft at: https://portal.azure.com/#home
  Search or click "App registrations"
  Click "+ New registration"
    == Name: COS OneDrive App
    == Supported account types:
         Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)
    == Redirect URI (optional)
         http://localhost:5000/oauth/callback/onedrive/
  => sent to new application registration page
    ==> "Note Application (client) ID", that will be the `ONEDRIVE_KEY` value provided to the OD provider.
  => Click on "Certificates & secrets"
    => Click "+ New client secret"
       Choose term limits
       Save
       Copy "Value" of new secret.  In `~/addons/onedrive/settings/local.py`, set `ONEDRIVE_SECRET` to the copied value.
  => Click on "API permissions"
    => Click "+ Add a permission"
      => Select "Microsoft Graph"
      => Select "Delegated Permission"
        => "User.Read" is selected by default.  Add "offline_access", "Files.Read",
           "Files.Read.All", "Files.ReadWrite"
