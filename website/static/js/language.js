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

