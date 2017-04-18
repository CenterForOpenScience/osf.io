var SUPPORT_EMAIL = 'support@osf.io';
var SUPPORT_LINK = '<a href="mailto:' + SUPPORT_EMAIL + '">' + SUPPORT_EMAIL +'</a>';

var REFRESH_OR_SUPPORT = 'Please refresh the page and try again or contact ' + SUPPORT_LINK + ' if the problem persists.';

module.exports = {
    REFRESH_OR_SUPPORT: REFRESH_OR_SUPPORT,
    SUPPORT_LINK: SUPPORT_LINK,
    // TODO
    makePublic: null,
    makePrivate: null,
    registrations: {
        registrationFailed: 'Registration failed. If this problem persists, please contact ' + SUPPORT_EMAIL + '.',
        invalidEmbargoTitle: 'Invalid embargo end date',
        invalidEmbargoMessage: 'Please choose a date more than two days, but less than four years, from today.',
        registerConfirm: 'Before you continue...',
        registerSkipAddons: 'If you choose to continue with the registration at this time we will exclude the contents of any addons that are not copyable. These files will not appear in the final registration.',
        registerFail: 'There was a problem completing your registration. Please try again later. If this should not have occurred and the issue persists, please report it to ' + SUPPORT_LINK + '.',
        submitForReviewFail: 'There was a problem submitting this draft for review right now. Please try again later. If this should not have occurred and the issue persists, please report it to ' + SUPPORT_LINK + '.',
        beforeEditIsApproved: 'This draft registration is currently approved. Please note that if you make any changes (excluding comments) this approval status will be revoked and you will need to submit for approval again.',
        beforeEditIsPendingReview: 'This draft registration is currently pending review. Please note that if you make any changes (excluding comments) this request will be cancelled and you will need to submit for approval again.',
        loadDraftsFail: 'There was a problem loading draft registrations at this time. ' + REFRESH_OR_SUPPORT,
        deleteDraftFail: 'There was a problem deleting this draft. ' + REFRESH_OR_SUPPORT,
        loadMetaSchemaFail: 'There was a problem loading registration templates at this time. ' + REFRESH_OR_SUPPORT
    },
    Addons: {
        dataverse: {
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact ' + SUPPORT_LINK + ' if the problem persists.',
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
            authError: 'Sorry, but there was a problem connecting to that instance of Dataverse. It ' +
                'is likely that the instance hasn\'t been upgraded to Dataverse 4.0. If you ' +
                'have any questions or believe this to be an error, please contact ' +
                'support@osf.io.',
            authInvalid: 'Your Dataverse API token is invalid.',
            authSuccess: 'Your Dataverse account was linked.',
            datasetDeaccessioned: 'This dataset has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.',
            forbiddenCharacters: 'This dataset cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.',
            setDatasetError: 'Could not connect to this dataset.',
            widgetInvalid: 'The credentials associated with this Dataverse account ' +
                'appear to be invalid.',
            widgetError: 'There was a problem connecting to the Dataverse.'
        },
        dropbox: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Dropbox account? ' +
                'This will revoke access to Dropbox for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect Dropbox account at this time',
        },
        figshare: {
            confirmDeauth: 'Are you sure you want to disconnect the figshare account? ' +
                'This will revoke access to figshare for all projects you have ' +
                'associated with this account.',
        },
        // TODO
        github: {
            confirmDeauth: 'Are you sure you want to disconnect the GitHub account? ' +
                'This will revoke access to GitHub for all projects you have ' +
                'associated with this account.',
        },
        gitlab: {
            confirmDeauth: 'Are you sure you want to disconnect the GitLab account? ' +
                'This will revoke access to GitLab for all projects you have ' +
                'associated with this account.',
        },
        s3:{
            authError: 'Could not connect to Amazon S3 at this time. Please try again later.',
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact ' + SUPPORT_LINK + ' if the problem persists.',
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Are you sure you want to disconnect the Google Drive account? ' +
                'This will revoke access to Google Drive for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect the Google Drive account at this time',
        },
        owncloud: {
            authError: 'Invalid ownCloud server',
            authInvalid: 'Invalid credentials. Please enter a valid username and password.',
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact ' + SUPPORT_LINK + ' if the problem persists.',
            confirmAuth : 'Are you sure you want to authorize this project with your ownCloud credentials?',
            updateAccountsError : 'Could not retrieve ownCloud account list at ' +
                        'this time. Please refresh the page. If the problem persists, email ' +
                        '<a href="mailto:support@osf.io">support@osf.io</a>.',
            submitSettingsSuccess : 'Folder Successfully linked',
        },
    },
    apiOauth2Application: {
        discardUnchanged: 'Are you sure you want to discard your unsaved changes?',
        deactivateConfirm: 'Are you sure you want to deactivate this application for all users and revoke all access tokens? This cannot be reversed.',
        deactivateError: 'Could not deactivate application. Please wait a few minutes and try again, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        dataFetchError: 'Data not loaded. ' + REFRESH_OR_SUPPORT,
        dataListFetchError: 'Could not load list of developer applications at this time. ' + REFRESH_OR_SUPPORT,
        dataSendError: 'Error sending data to the server. Check that all fields are valid, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        creationSuccess: 'Successfully registered new application',
        dataUpdated: 'Application data updated',
        resetSecretConfirm: 'Are you sure you want to reset the client secret? This cannot be reversed. Your application will be unusable until it is updated with the new client secret, and all users must reauthorize access. Previously issued access tokens will no longer work.',
        resetSecretError: 'Could not reset client secret. Please wait a few minutes and try again, or contact ' + SUPPORT_LINK + 'if the problem persists.',
    },
    apiOauth2Token: {
        discardUnchanged: 'Are you sure you want to discard your unsaved changes?',
        deactivateConfirm: 'Are you sure you want to deactivate this token? This cannot be reversed.',
        deactivateError: 'Could not deactivate token. Please wait a few minutes and try again, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        dataFetchError: 'Data not loaded. ' + REFRESH_OR_SUPPORT,
        dataListFetchError: 'Could not load list of personal access tokens at this time. ' + REFRESH_OR_SUPPORT,
        dataSendError: 'Error sending data to the server: check that all fields are valid, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        creationSuccess: 'Successfully generated new personal access token. This token will never expire. This token should never be shared with others. If it is accidentally revealed publicly, it should be deactivated immediately.',
        dataUpdated: 'Token data updated'
    },
    projectSettings: {
        updateSuccessMessage: 'Successfully updated project settings.',
        updateErrorMessage400: 'Error updating project settings. Check that all fields are valid.',
        updateErrorMessage: 'Could not update project settings. ' + REFRESH_OR_SUPPORT,
        instantiationErrorMessage: 'Trying to instantiate ProjectSettings view model without an update URL'
    }
};
