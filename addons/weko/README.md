# OSF WEKO Add-on: Custom Add-ons for OSF in Japan

## License

[Apache License Version 2.0](LICENSE) © 2024 National Institute of Informatics

## Setting up WEKO Add-on

An administrator of an institution can enable the WEKO add-on from the admin panel and set up the OAuth2 client information for WEKO. The members of the institution can link their WEKO account with their OSF account.

If the WEKO is non-HTTPS sites, you should set the `OAUTHLIB_INSECURE_TRANSPORT` environment variable for osf.io:

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
    - Items can be uploaded.
 - For non-contributors, when a node is public:
    - The user can access the content of indices and items.
 - For non-contributors, when a node is private, there is no access to the WEKO add-on.
