var SUPPORT_EMAIL = 'support@osf.io';
var SUPPORT_EMAIL_MAILTO = '<a href="mailto:' + SUPPORT_EMAIL + '">' + SUPPORT_EMAIL +'</a>';

module.exports = {
    // TODO
    makePublic: null,
    makePrivate: null,
    registrations: {
        registrationFailed: 'Registration failed. If this problem persists, please contact ' + SUPPORT_EMAIL + '.',
        invalidEmbargoTitle: 'Invalid embargo end date',
        invalidEmbargoMessage: 'Please choose a date more than two days, but less than four years, from today.',
        registerConfirm: 'Are you sure you want to register this project?',
        registerSkipAddons: 'If you choose to continue with the registration at this time we will exclude the contents of any addons that are not copyable. These files will not appear in the final registration.',
        registerFail: 'There was a problem completing your registration right now. Please try again later. If this should not have occurred and the issue persists, please report it to ' + SUPPORT_EMAIL_MAILTO,
        submitForReviewFail: 'There was a problem submitting this draft for review right now. Please try again later. If this should not have occurred and the issue persists, please report it to ' + SUPPORT_EMAIL_MAILTO,
        beforeEditIsApproved: 'This draft registration is currently approved. Please note that if you make any changes (excluding comments) this approval status will be revoked and you will need to submit for approval again.',
        beforeEditIsPendingReview: 'This draft registration is currently pending review. Please note that if you make any changes (excluding comments) this request will be cancelled and you will need to submit for approval again.'
    },
    Addons: {
        dataverse: {
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact ' + SUPPORT_EMAIL_MAILTO + ' if the problem persists.',
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
        s3: {
            confirmDeauth: 'Are you sure you want to disconnect the S3 account? ' +
                'This will revoke access to S3 for all projects you have ' +
                'associated with this account.',
        },
        box: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Box account? ' +
                'This will revoke access to Box for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect the Box account at this time',
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Are you sure you want to disconnect the Google Drive account? ' +
                'This will revoke access to Google Drive for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect the Google Drive account at this time',
        }
    }
};
