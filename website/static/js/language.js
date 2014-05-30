(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery', 'osfutils'], factory);
    } else {
        factory(jQuery);
    }
}(this, function($) {
    $.osf.Language = {

        // TODO
        makePublic: null,
        makePrivate: null,

        Addons: {
            dataverse: {
                userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                    'contact <a href="mailto: support@cos.io">support@cos.io</a> if the ' +
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
                authSuccess: 'Your dataverse account was linked.'
            },
            dropbox: {
                // Shown on clicking "Delete Access Token" for dropbox
                confirmDeauth: 'Are you sure you want to delete your Dropbox access ' +
                    'key? This will revoke access to Dropbox for all projects you have ' +
                    'authorized delete your access token from Dropbox.',
                deauthError: 'Could not deauthorize Dropbox at this time',
                deauthSuccess: 'Deauthorized Dropbox.'
            },
            // TODO
            github: {

            },
            s3: {

            }
        }
    };
}));

