var SUPPORT_EMAIL = 'support@osf.io';

module.exports = {
    // TODO
    makePublic: null,
    makePrivate: null,
    registrations: {
        registrationFailed: 'Registration failed. If this problem persists, please contact ' + SUPPORT_EMAIL + '.',
        invalidEmbargoTitle: 'Invalid embargo end date',
        invalidEmbargoMessage: 'Please choose a date more than two days, but less than four years, from today.',
        registerConfirm: 'Are you sure you want to register this project?',
        registerSkipAddons: 'If you choose to continue with the registration at this time we will exclude the contents of any addons that are not copyable. These files will not appear in the final registration.'
    },
    Addons: {
        dataverse: {
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: ' + SUPPORT_EMAIL + '">' + SUPPORT_EMAIL + '</a> if the ' +
                'problem persists.',
            confirmUserDeauth: 'Are you sure you want to unlink your Dataverse ' +
                'Account? This will revoke access to Dataverse for all ' +
                'projects you have authorized.',
            confirmNodeDeauth: 'Are you sure you want to unlink this Dataverse Account? This will ' +
                'revoke the ability to view, download, modify, and upload files ' +
                'to studies on the Dataverse from the OSF. This will not remove your ' +
                'Dataverse authorization from your <a href="/settings/addons/">user settings</a> ' +
                'page.',
            deauthError: 'Could not disconnect the Dataverse Account at this time.',
            deauthSuccess: 'Succesfully disconnected the connected Dataverse Account.',
            authError: 'There was a problem connecting to the Dataverse.',
            authInvalid: 'Your Dataverse API token is invalid.',
            authSuccess: 'Your Dataverse Account was linked.',
            datasetDeaccessioned: 'This dataset has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.',
            forbiddenCharacters: 'This dataset cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.',
            setDatasetError: 'Could not connect to this dataset.',
            widgetInvalid: 'The credentials associated with this Dataverse Account ' +
                'appear to be invalid.',
            widgetError: 'There was a problem connecting to the Dataverse.'
        },
        dropbox: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Dropbox Account? ' +
                'This will revoke access to Dropbox for all projects you have ' +
                'authorized.',
            deauthError: 'Could not disconnect Dropbox Account at this time',
            deauthSuccess: 'Successfully disconnected the connected Dropbox Account.'
        },
        // TODO
        github: {

        },
        s3: {

        },
        box: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Box Account? ' +
                'This will revoke access to Box for all projects you have ' +
                'authorized.',
            deauthError: 'Could not disconnect the Box Account at this time',
            deauthSuccess: 'Successfully disconnected the connected Box Account.'
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Are you sure you want to disconnect the Google Drive Account? ' +
                'This will revoke access to Google Drive for all projects you have ' +
                'authorized.',
            deauthError: 'Could not disconnect the Google Drive Account at this time',
            deauthSuccess: 'Successfully disconnected the connected Google Drive Account.'
        }
    }
};
