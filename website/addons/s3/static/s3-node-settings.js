(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else if (typeof $script === 'function') {
        global.s3NodeSettings = factory(ko, jQuery);
        $script.done('s3NodeSettings');
    } else {
        global.s3NodeSettings = factory(ko, jQuery);
    }
}(this, function(ko, $) {
    'use strict';

    function S3NodeSettingsViewModel(data){
        var self = this;

        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');
        self.userHasAuth = ko.observable(false);
        self.isRegistration = ko.observable(false);
        self.nodeHasAuth = ko.observable(false);
        self.userIsOwner = ko.observable(false);
        self.bucketList = ko.observableArray([]);
        self.ownerURL = ko.observable('');
        self.ownerName = ko.observable('');
        self.accessKey = ko.observable('');
        self.secretKey = ko.observable('');
        self.selectedBucket = ko.observable('-----');

        self.updateFromData = function(data) {
            self.userHasAuth(data['user_has_auth']);
            self.isRegistration(data['is_registration']);
            self.nodeHasAuth(data['node_has_auth']);
            self.userIsOwner(data['user_is_owner']);
            self.bucketList(data['bucket_list']);
            self.ownerURL(data['owner_url'])
            self.ownerName(data['owner_name'])
            $('form#s3AddonNodeScope').show();
        };

        self.fetchFromServer = function() {
            $.ajax({
                url: url + 'serialize/', type: 'GET', dataType: 'json',
                success: function(response) {
                    self.updateFromData(response.result);
                },
                error: function(xhr, textStatus, error) {
                    self.changeMessage('Could not retrieve s3 settings at ' +
                    'this time. Please refresh ' +
                    'the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.',
                    'text-warning');
                    Raven.captureMessage('Could not GET s3 settings', {
                        url: url + 'serialize/',
                        textStatus: textStatus,
                        error: error
                    });
                }
            });
        };

        // Initial fetch from server
        self.fetchFromServer();

        self.makeNewBucket = function() {
            self.newBucket();
        };

        self.s3RemoveToken = function() {
            bootbox.confirm({
                title: 'Deauthorize S3?',
                message: 'Are you sure you want to remove this S3 authorization?',
                callback: function(confirm) {
                    if(confirm) {
                        self.removeNodeAuth();
                    }
                }
            });
        };

        self.submitSettingsNoAuth = function() {

            url = nodeApiUrl + 's3/authorize/'

            $.osf.postJSON(
                url,
                self.serialize()
            ).done(function() {
                window.setTimeout(window.location.reload.bind(window.location), 5000);
                self.changeMessage('Settings updated', 'text-success', 5000);
            }).fail(function(xhr) {
                var message = 'Error: ';
                var response = JSON.parse(xhr.responseText);
                if (response && response.message) {
                    message += response.message;
                } else {
                    message += 'Settings not updated.';
                }
                self.changeMessage(message, 'text-danger', 5000);
            });

            return false;
        };

        self.submitSettingsAuth = function(){

            if(self.selectedBucket() != '-----'){
                url = nodeApiUrl + 's3/settings/'
                $.osf.postJSON(
                    url,
                    self.serialize()
                ).done(function() {
                    self.changeMessage('Settings updated', 'text-success', 5000);
                    window.location.reload();
                }).fail(function(xhr) {
                    var message = 'Error: ';
                    var response = xhr.responseText;
                    if (response && response.message) {
                        message += response.message;
                    } else {
                        message += 'Settings not updated.';
                    }
                    self.changeMessage(message, 'text-danger', 5000);
                });
            } else {
                self.changeMessage('Settings not updated. Please select a bucket', 'text-danger', 3000)
            }

            return false;
        };
        
        self.newBucket = function() {
            var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

            bootbox.prompt('Name your new bucket', function(bucketName) {
                if (!bucketName) {
                    return;
                } else if (isValidBucket.exec(bucketName) == null) {
                    bootbox.confirm({
                        title: 'Invalid bucket name',
                        message: 'Sorry, that\'s not a valid bucket name. Try another name?',
                        callback: function(result) {
                            if(result) {
                                newBucket();
                            }
                        }
                    });
                } else {
                    bucketName = bucketName.toLowerCase();
                    $.osf.postJSON(
                        nodeApiUrl + 's3/newbucket/',
                        {bucket_name: bucketName}
                    ).done(function() {
                        window.setTimeout(window.location.reload.bind(window.location), 2000);
                        self.changeMessage('Bucket created.', 'text-success', 5000);
                    }).fail(function(xhr) {
                        var message = JSON.parse(xhr.responseText).message;
                        if(!message) {
                            message = 'Looks like that name is taken. Try another name?';
                        }
                        bootbox.confirm({
                            title: 'Duplicate bucket name',
                            message: message,
                            callback: function(result) {
                                if(result) {
                                    //newBucket(); //Do nothing, else it hangs here
                                }
                            }
                        });
                    });
                }
            });
        }

        self.removeNodeAuth = function() {
            $.ajax({
                type: 'DELETE',
                url: nodeApiUrl + 's3/settings/',
                contentType: 'application/json',
                dataType: 'json'
            }).done(function() {
                window.location.reload();
            }).fail(
                $.osf.handleJSONError
            );
        }

        self.importNodeAuth = function() {
            $.osf.postJSON(
                nodeApiUrl + 's3/import-auth/',
                {}
            ).done(function() {
                window.location.reload();
            }).fail(
                $.osf.handleJSONError
            );
        }

        self.serialize = function(){
            var rv = {};
            rv['s3_bucket'] = self.selectedBucket()[0];
            rv['access_key'] = self.accessKey();
            rv['secret_key'] = self.secretKey();
            return rv;
        };

        self.s3ImportToken = function() {
            self.importNodeAuth();
        };

                /** Change the flashed message. */
        self.changeMessage = function(text, css, timeout) {
            self.message(text);
            var cssClass = css || 'text-info';
            self.messageClass(cssClass);
            if (timeout) {
                // Reset message after timeout period
                window.setTimeout(function() {
                    self.message('');
                    self.messageClass('text-info');
                }, timeout);
            }
        };
    }

    self.S3NodeSettingsModule = function(selector, url) {
        self.url = url;
        this.S3NodeSettingsViewModel = new S3NodeSettingsViewModel(url);
        $.osf.applyBindings(this.S3NodeSettingsViewModel, selector);
    }
    return S3NodeSettingsModule;

}));
