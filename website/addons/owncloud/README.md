OSF ownCloud Addon


## Setup:
1. Copy settings/local-dist.py to settings/local.py and change the necessary settings.
2. Make sure to list your server under `trusted_servers`
...

## Enabling the addon for development

 - Install gpg.
 ```sh
 $ brew install gpg
 ```
 - Import a private key into your GnuPG keyring.
```sh
$ invoke encryption
```
