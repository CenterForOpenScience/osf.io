module.exports = {
    // TODO
    makePublic: null,
    makePrivate: null,

    Addons: {
        dataverse: {
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.',
            confirmUserDeauth: 'Are you sure you want to unlink your Dataverse ' +
                'account? This will revoke access to Dataverse for all ' +
                'projects you have authorized.',
            confirmNodeDeauth: 'Are you sure you want to unlink this Dataverse account? This will ' +
                'revoke the ability to view, download, modify, and upload files ' +
                'to studies on the Dataverse from the OSF. This will not remove your ' +
                'Dataverse authorization from your <a href="/settings/addons/">user settings</a> ' +
                'page.',
            deauthError: 'Could not unlink Dataverse at this time.',
            deauthSuccess: 'Unlinked your Dataverse account.',
            authError: 'There was a problem connecting to the Dataverse.',
            authInvalid: 'Your Dataverse username or password is invalid.',
            authSuccess: 'Your Dataverse account was linked.',
            studyDeaccessioned: 'This study has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.',
            forbiddenCharacters: 'This study cannot be connected due to forbidden characters ' +
                'in one or more of the study\'s file names. This issue has been forwarded to our ' +
                'development team.',
            setStudyError: 'Could not connect to this study.',
            widgetInvalid: 'The Dataverse credentials associated with ' +
                'this node appear to be invalid.',
            widgetError: 'There was a problem connecting to the Dataverse.'
        },
        dropbox: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to delete your Dropbox access ' +
                'key? This will revoke access to Dropbox for all projects you have ' +
                'authorized.',
            deauthError: 'Could not deauthorize Dropbox at this time',
            deauthSuccess: 'Deauthorized Dropbox.'
        },
        // TODO
        github: {

        },
        s3: {

        },
        box: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to delete your Box access ' +
                'key? This will revoke access to Box for all projects you have ' +
                'authorized.',
            deauthError: 'Could not deauthorize Box at this time',
            deauthSuccess: 'Deauthorized Box.'
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Are you sure you want to delete your Google Drive access ' +
                'key? This will revoke access to Google Drive for all projects you have ' +
                'authorized.',
            deauthError: 'Could not deauthorize Google Drive at this time',
            deauthSuccess: 'Deauthorized Google Drive.'
        }
    }
};
