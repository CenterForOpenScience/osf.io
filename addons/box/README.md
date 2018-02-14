# OSF Box Addon

## Enabling the addon for development

### Setting up Box for provider access
1. Go to https://developer.box.com/ and create an account (You must make a developer account, not a regular box account)
2. Verify your account and finish setting it up (The verification email may take a few minutes to show up)
3. Click on your profile and go to  > "Account Settings", then go to > "Dev Console"
4. Create a new custom app with "Standard OAuth 2.0 (User Authentication)""
5. Find your Client ID and Client secret and make a note of them
6. Right below your Client ID and Secret fields, add <http://localhost:5000/oauth/callback/box/> as  your Redirect URI


### Enabling on OSF
1. If `addons/box/settings/local.py` does not yet exist, create a local box settings file with `cp addons/box/settings/local-dist.py addons/box/settings/local.py`
2. Enter your Box `client_id` and `client_secret` as `BOX_KEY` and `BOX_SECRET` in `addons/box/settings/local.py`.
3. Ensure `"box"` exists in the addons list in `"addons.json"`
4. Enable your new Box provider
