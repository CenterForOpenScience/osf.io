# OSF ownCloud Addon

## Deprecation Warning: ./website/addons has been moved to ./addons
## Please configure in the new location


## Setup:
1. Copy settings/local-dist.py to settings/local.py and change the necessary settings.
2. The setting `DEFAULT_HOSTS` can be set to a list of known hosts that satisfies [OCS1.7](https://www.freedesktop.org/wiki/Specifications/open-collaboration-services-1.7/). While this is not necessary, a default list can be used to provide users with suggested hosts.
3. Make sure GnuPG is enabled as below:
