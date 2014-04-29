# OSF Dataverse Add-on

A couple notes before beginning:
 - The add-on uses a modified version of the dataverse python client.
 - The add-on is currently configured to use the test server. This can be changed in settings/defaults.py

To link a Dataverse study to a node (project or component):
 1. Go to user settings. Under "Add-ons", select "Dataverse" and click submit.
 2. Under "Configure Add-ons", Enter valid Dataverse credentials and click submit.
 3. Go to the the node settings page. Under "Select Add-ons", select "Dataverse" and click submit.
 4. Under "Configure Add-ons", select a Dataverse. Only released Dataverses are selectable.
 5. Once the page refreshes, select a study. Your Dataverse study will be linked.

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