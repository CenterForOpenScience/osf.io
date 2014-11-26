(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else if (typeof $script === 'function') {
        global.s3UserSettings = factory(ko, jQuery);
        $script.done('s3UserSettings');
    } else {
        global.s3UserSettings = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function S3UserSettingsViewModel(){
        var self = this;

        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        self.accessKey = ko.observable('');
        self.secretKey = ko.observable('');
        self.userHasAuth = ko.observable(false);

        /**
         * Update the view model from data returned from the server.
         */
        self.updateFromData = function(data) {
            self.userHasAuth(data['has_auth']);
            $('form#s3AddonUserScope').show();
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: '/api/v1/s3/settings/', type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response);
                },
                error: function(xhr, textStatus, error) {
                    self.changeMessage('Could not retrieve s3 settings at ' +
                        'this time. Please refresh ' +
                        'the page. If the problem persists, email ' +
                        '<a href="mailto:support@osf.io">support@osf.io</a>.',
                        'text-warning');
                    Raven.captureMessage('Could not GET s3 settings', {
                        url: '/api/v1/s3/config/',
                        textStatus: textStatus,
                        error: error
                    });
                }
            });
        };

        // Initial fetch from server
        self.fetchFromServer();

        /** Prompts user about deleting their authorization */
        self.s3RemoveAccess = function(){
            bootbox.confirm({
                title: 'Remove access key?',
                message: 'Are you sure you want to remove your Amazon Simple Storage Service access key? ' +
                        'This will revoke access to Amazon S3 for all projects you have authorized and ' +
                        'delete your access token from Amazon S3. Your OSF collaborators will not be able ' +
                        'to write to Amazon S3 buckets or view private buckets that you have authorized.',
                callback: function(result) {
                    if(result) {
                        self.deleteToken();
                    }
                }
            });
        };

        self.submitSettings = function(){
            $.osf.postJSON(
                '/api/v1/settings/s3/',
                self.serialize()
            ).done(function() {
                window.location.reload();
            }).fail(function(response) {
                var message = 'Error: ';
                var response = JSON.parse(response.responseText);
                if (response && response.message) {
                    message += response.message;
                } else {
                    message += 'Settings not updated.';
                }
                self.changeMessage(message, 'text-danger', 1000);
            });
            return false;      
        };

        /** Deletes user credentials*/
        self.deleteToken = function(){
            $.ajax({
                type: 'DELETE',
                url: '/api/v1/settings/s3/',
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                        window.location.reload();
                },
                error: function(xhr) {
                    var response = JSON.parse(xhr.responseText);
                    if (response && response.message) {
                        if(response.message === 'reload'){
                            window.location.reload();
                        }
                        else{
                            message = response.message;
                        }
                    } else {
                        message = 'Error: Keys not removed';
                    }
                    self.changeMessage(message, 'text-danger', 1000);
                }
            });
            return false;
        };

        /** Change the flashed message. */
        self.changeMessage = function(text, css, timeout) {
            self.message(text);
            var cssClass = css || 'text-info';
            self.messageClass(cssClass);
            if (timeout) {
                // Reset message after timeout period
                setTimeout(function() {
                    self.message('');
                    self.messageClass('text-info');
                }, timeout);
            }
        };

        /** Serialize form */
        self.serialize = function(){
            var rv = {};
            rv['access_key'] = self.accessKey();
            rv['secret_key'] = self.secretKey();
            return rv;
        };
    }

    function S3UserSettingsModule(selector) {
        this.S3UserSettingsViewModel = new S3UserSettingsViewModel();
        $.osf.applyBindings(this.S3UserSettingsViewModel, selector);
    }

    return S3UserSettingsModule;

}));