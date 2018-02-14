# OSF Dataverse Add-on

## Enabling the addon for development

Ensure `"dataverse"` exists in the addons list in `"addons.json"`

### Creating a Dataverse dataset on the test server

1. Go to https://demo.dataverse.org/ and create an account
2. On the homepage, click the "Add Data" > "Create Dataverse" button to create a Dataverse
3. Navigate to your newly created dataverse
4. Click on the publish button to publish the dataverse
5. On the Datasets tab, click "Create Dataset + Upload Data" and create a dataset
6. Click on your profile > "API Token" and create an API token. Make a note of it.

### Link a Dataverse dataset to a node (project or component):

1. Go to user settings. Under "Add-ons", select "Dataverse" and click submit.
2. Under "Configure Add-ons", select "other dataverse provider", and enter `demo.dataverse.org/` for the url. Enter your API Token.
3. Go to the the node settings page. Under "Select Add-ons", select "Dataverse" and click submit.
4. Under "Configure Add-ons", select a dataverse and dataset and click submit.

## Notes on privacy settings:
 - Only the user that linked his or her Dataverse account can change the Dataverse or dataset linked from that account. Other contributors can still deauthorize the node.
 - For contributors with write permission to the node:
    - The user can access the dataset title, doi, host Dataverse, and citation.
    - The draft version and most-recently published version of a dataset are accessible as separate lists.
    - Files from either the draft or published version can be viewed or downloaded.
    - Files from the draft version can be uploaded, updated, or deleted.
    - Draft versions can be published.
 - For non-contributors, when a node is public:
    - The user can access the dataset title, doi, host Dataverse, and citation.
    - Only the most-recently published version of the dataset is accessible.
        - If there are no published files, the dataset is not displayed.
    - Files from the published version can be viewed or downloaded.
 - For non-contributors, when a node is private, there is no access to the Dataverse add-on.
