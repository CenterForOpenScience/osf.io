'use strict';
var $ = require('jquery');
var bootbox = require('bootbox');

var FlatNodeConfig = require('js/flatNodeConfig').FlatNodeConfig;

var url = window.contextVars.node.urls.api + 's3/settings/';
new FlatNodeConfig('S3', '#s3Scope', url, 'bucket', {
    formatFolders: function(response) {
        return response.buckets
    },
    formatFolderName: function(folderName) {
        var newName = folderName.replace(/[^a-z0-9\d.-]+/g, '-');
        return newName
    },
    attemptRetrieval: function(self) {
         if (self.nodeHasAuth() && !self.validCredentials()) {
             debugger;
            var message = '';
            if(self.userIsOwner()) {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing S3 on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            } else {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.';
            }
            self.changeMessage(message, 'text-danger');
        }
    },
    findFolder: function(settings) {
        return (settings.has_bucket ? settings.bucket : null);
    },
    connectAccount: function(self, $osf) {
        bootbox.dialog({
            title: "Connect S3 Account",
            message: '<div class="form-group">' +
                '<label for="s3Addon">Access Key</label>' +
                '<input id="access_key" class="form-control" name="access_key" />' +
              '</div>' +
              '<div class="form-group">' +
                '<label for="s3Addon">Secret Key</label>' +
                '<input id="secret_key" type="password" class="form-control" name="secret_key" />' +
              '</div>',
            buttons: {
                success: {
                    label: "Submit",
                    callback: function() {
                        var accessKey = $('#access_key').val();
                        var secretKey = $('#secret_key').val();
                        return $osf.postJSON(
                            self.urls().create_auth, {
                                access_key: accessKey,
                                secret_key: secretKey
                        }).done(function (response) {
                                self.changeMessage('Successfully added S3 credentials.', 'text-success');
                                self.updateFromData(response);
                        }).fail(function (xhr, status, error) {
                            var message = 'Could not add S3 credentials at ' +
                                'this time. Please refresh the page. If the problem persists, email ' +
                                '<a href="mailto:support@osf.io">support@osf.io</a>.';
                            self.changeMessage(message, 'text-warning');
                            Raven.captureMessage('Could not add S3 credentials', {
                                url: self.urls().importAuth,
                                textStatus: status,
                                error: error
                            });
                        });
                    }
                }
            }
        }); 
    },
    importAccount: function(account_id, self, $osf) {
        return $osf.postJSON(
            self.urls().importAuth, {}
        ).done(function(response) {
            self.changeMessage('Successfully imported S3 credentials.', 'text-success');
            self.updateFromData(response);
        }).fail(function(xhr, status, error) {
            var message = 'Could not import S3 credentials at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not import S3 credentials', {
                url: self.urls().importAuth,
                textStatus: status,
                error: error
            });
        });
    }
});
