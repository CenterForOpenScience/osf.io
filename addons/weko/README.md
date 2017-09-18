# OSF WEKO Add-on: Custom Add-ons for OSF in Japan

## License

[Apache License Version 2.0](LICENSE) © 2017 National Institute of Informatics

## Setting up WEKO Add-on

You should change `addons/weko/settings/local.py` as below:

```
REPOSITORIES = {'sample.repo.nii.ac.jp':
                 {'host': 'http://sample.repo.nii.ac.jp/weko/sword/',
                  'client_id': 'testclient2016a', 'client_secret': 'testpass2016a',
                  'authorize_url': 'http://sample.repo.nii.ac.jp/oauth/authorize.php',
                  'access_token_url': 'http://sample.repo.nii.ac.jp/oauth/token.php'}}
REPOSITORY_IDS = list(sorted(REPOSITORIES.keys()))
```

If `REPOSITORIES` includes non-HTTPS sites,
you should set the `OAUTHLIB_INSECURE_TRANSPORT` environment variable for osf.io:

```
OAUTHLIB_INSECURE_TRANSPORT=1
```

## Linking an index on WEKO with your project

1. Go to user settings. Under "Add-ons", select "WEKO" and click submit.
2. Under "Configure Add-ons", select your the repository and log-in by your account.
3. Go to the the node settings page. Under "Select Add-ons", select "WEKO" and click submit.
4. Under "Configure Add-ons", select your index and click submit.

Notes on privacy settings:
 - Only the user that linked his or her WEKO account can change the index linked from that account. Other contributors can still deauthorize the node.
 - For contributors with write permission to the node:
    - The user can access the content of indices and items.
    - Items in index can be viewed.
    - Items can be uploaded, or deleted.
 - For non-contributors, when a node is public:
    - The user can access the content of indices and items.
 - For non-contributors, when a node is private, there is no access to the WEKO add-on.
