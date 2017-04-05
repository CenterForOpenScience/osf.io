# OSF DMPTool Addon

Enabling the addon for development

1. Create a local dmptool settings file with `cp addons/dmptool/settings/local-dist.py addons/dmptool/setings/local.py`
2. Ensure `"dmptool"` exists in the addons list in `"addons.json"`

Note that unlike many other add-ons, there is no need to acquire any developer keys for the DMPTool addon to run. (The DMPTool API makes use of API tokens that have been assigned to the DMPTool user.)