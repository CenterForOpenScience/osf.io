# OSF Dataverse Add-on

Enabling the addon for development

 - Install gpg.
 ```sh
 $ brew install gpg
 ```
 - Import a private key into your GnuPG keyring.
```sh
$ invoke encryption
```
 - In `website/settings/local.py` add, `"dataverse"` to `ADDONS_REQUESTED`.

Creating a Dataverse study on the test server

1. Go to http://dvn-demo.iq.harvard.edu/ and create an account
2. On the homepage, click the "Create Dataverse" button to create a Dataverse
3. Click the options icon on the Dataverse page
4. On the Settings tab, set "Dataverse Release Settings" to "Released" and save changes.
5. On the Studies tab, click "Create Study + Upload Data" and create a study (only title is required)

To link a Dataverse study to a node (project or component):

1. Go to user settings. Under "Add-ons", select "Dataverse" and click submit.
2. Under "Configure Add-ons", enter your Dataverse credentials and click submit.
3. Go to the the node settings page. Under "Select Add-ons", select "Dataverse" and click submit.
4. Under "Configure Add-ons", select a Dataverse and study and click submit.

Notes on privacy settings:
 - Only the user that linked his or her Dataverse account can change the Dataverse or study linked from that account. Other contributors can still deauthorize the node.
 - For contributors with write permission to the node:
    - The user can access the study title, doi, host Dataverse, and citation.
    - The draft version and most-recently released version of a study are accessible as separate lists.
    - Files from either the draft or released version can be viewed or downloaded.
    - Files from the draft version can be uploaded, updated, or deleted.
    - Draft versions can be released.
 - For non-contributors, when a node is public:
    - The user can access the study title, doi, host Dataverse, and citation.
    - Only the most-recently released version of the study is accessible.
        - If there are no released files, the study is not displayed.
    - Files from the released version can be viewed or downloaded.
 - For non-contributors, when a node is private, there is no access to the Dataverse add-on.