'use strict';
var ko = require('knockout');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var $modal = $('#s3InputCredentials');

var s3Settings = require('json!./settings.json');

var defaultSettings = {
    url: '',
    encryptUploads: s3Settings.encryptUploads,
    bucketLocations: s3Settings.bucketLocations
};

var ViewModel = function(selector, settings) {
    var self = this;

    self.url = settings.url;
    self.selector = selector;
    self.settings = $.extend({}, defaultSettings, settings);

    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.ownerName = ko.observable('');
    self.validCredentials = ko.observable(true);

    self.urls = ko.observable({});
    self.loadedSettings = ko.observable(false);
    self.bucketList = ko.observableArray([]);
    self.loadedBucketList = ko.observable(false);
    self.currentBucket = ko.observable('');
    self.selectedBucket = ko.observable('');
    self.encryptUploads = ko.observable(self.settings.encryptUploads);

    self.accessKey = ko.observable('');
    self.secretKey = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);
    self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
    self.node_message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewBucket = ko.pureComputed(function() {
        return self.userHasAuth() && self.userIsOwner();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth();
    });
    self.showCreateCredentials = ko.pureComputed(function() {
        return self.loadedSettings() && (!self.nodeHasAuth() && !self.userHasAuth());
    });
    self.canChange = ko.pureComputed(function() {
        return self.userIsOwner() && self.nodeHasAuth();
    });
    self.allowSelectBucket = ko.pureComputed(function() {
        return (self.bucketList().length > 0 || self.loadedBucketList()) && (!self.loading());
    });
    self.saveButtonText = ko.pureComputed (function(){
        return self.loading()? 'Saving': 'Save';
    });
};

ViewModel.prototype.toggleSelect = function() {
    var self = this;
    self.showSelect(!self.showSelect());
    return self.updateBucketList();
};

ViewModel.prototype.updateBucketList = function(){
    var self = this;
    return self.fetchBucketList()
        .done(function(buckets){
            self.bucketList(buckets);
            self.selectedBucket(self.currentBucket());
        });
};

/**
 * Tests if the given string is a valid Amazon S3 bucket name.  Supports two modes: strict and lax.
 * Strict is for bucket creation and follows the guidelines at:
 *
 *   http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
 *
 * However, the US East (N. Virginia) region currently permits much laxer naming rules.  The S3
 * docs claim this will be changed at some point, but to support our user's already existing
 * buckets, we provide the lax mode checking.
 *
 * Strict checking is the default.
 *
 * @param {String} bucketName user-provided name of bucket to validate
 * @param {Boolean} laxChecking whether to use the more permissive validation
 */
var isValidBucketName = function(bucketName, laxChecking) {
    if (laxChecking === true) {
        return /^[a-zA-Z0-9.\-_]{1,255}$/.test(bucketName);
    }
    var label = '[a-z0-9]+(?:[a-z0-9\-]*[a-z0-9])?';
    var strictBucketName = new RegExp('^' + label + '(?:\\.' + label + ')*$');
    var isIpAddress = /^[0-9]+(?:\.[0-9]+){3}$/;
    return bucketName.length >= 3 && bucketName.length <= 63 &&
        strictBucketName.test(bucketName) && !isIpAddress.test(bucketName);
};

ViewModel.prototype.selectBucket = function() {
    var self = this;

    self.loading(true);

    var ret = $.Deferred();
    if (!isValidBucketName(self.selectedBucket(), true)) {
        self.loading(false);
        bootbox.alert({
            title: 'Invalid bucket name',
            message: 'Amazon S3 buckets can contain lowercase letters, numbers, and hyphens separated by' +
            ' periods.  Please try another name.',
        });
        ret.reject();
    } else {
        $osf.putJSON(
                self.urls().set_bucket, {
                    's3_bucket': self.selectedBucket(),
                    'encrypt_uploads': self.encryptUploads()
                }
            )
            .done(function (response) {
                self.updateFromData(response);
                self.changeMessage('Successfully linked S3 bucket "' + self.currentBucket() + '". Go to the <a href="' +
                    self.urls().files + '">Files page</a> to view your content.', 'text-success', null, true);
                self.loading(false);
                ret.resolve(response);
            })
            .fail(function (xhr, status, error) {
                self.loading(false);
                var message = 'Could not change S3 bucket at this time. ' +
                    'Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
                self.changeMessage(message, 'text-danger', null, true);
                Raven.captureMessage('Could not set S3 bucket', {
                    url: self.urls().setBucket,
                    textStatus: status,
                    error: error
                });
                ret.reject();
            });
    }
    return ret.promise();
};

ViewModel.prototype._deauthorizeNodeConfirm = function() {
    var self = this;
    return $.ajax({
        type: 'DELETE',
        url: self.urls().deauthorize,
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        self.updateFromData(response);
        self.changeMessage('Disconnected S3.', 'text-warning', 3000, true);
    }).fail(function(xhr, status, error) {
        var message = 'Could not disconnect S3 at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger', null, true);
        Raven.captureMessage('Could not remove S3 authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disconnect S3 Account?',
        message: 'Are you sure you want to remove this S3 account?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        },
        buttons:{
            confirm:{
                label: 'Disconnect',
                className: 'btn-danger'
            }
        }
    });
};

ViewModel.prototype._importAuthConfirm = function() {
    var self = this;
    return $osf.putJSON(
        self.urls().import_auth, {}
    ).done(function(response) {
        self.changeMessage('Successfully imported S3 credentials.', 'text-success', null, true);
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        var message = 'Could not import S3 credentials at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger', null, true);
        Raven.captureMessage('Could not import S3 credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });

};

ViewModel.prototype.connectExistingAccount = function(accountId) {
    var self = this;
    return $osf.putJSON(
            self.urls().import_auth,
            {'external_account_id': accountId}
    ).done(function() {
            if($osf.isIE()){
                window.location.hash = '#configureAddonsAnchor';
            }
            window.location.reload();
    }).fail(
        $osf.handleJSONError
    );
};

ViewModel.prototype.importAuth = function() {
    var self = this;
    return $.get('/api/v1/settings/s3/accounts/'
            ).done(function(data){
                var accounts = data.accounts.map(function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                });
                if (accounts.length > 1) {
                    bootbox.prompt({
                        title: 'Choose Amazon S3 Account to Import',
                        inputType: 'select',
                        inputOptions: ko.utils.arrayMap(
                            accounts,
                            function(item) {
                                return {
                                    text: $osf.htmlEscape(item.name),
                                    value: item.id
                                };
                            }
                        ),
                        value: accounts[0].id,
                        callback: function(accountId) {
                            self.connectExistingAccount(accountId);
                        },
                        buttons: {
                            confirm:{
                                label:'Import',
                            }
                        }
                    });
                } else {
                    bootbox.confirm({
                        title: 'Import Amazon S3 Account?',
                        message: 'Are you sure you want to link your S3 account with this project?',
                        callback: function(confirmed) {
                            if (confirmed) {
                                self.connectExistingAccount(accounts[0].id);
                            }
                        },
                        buttons: {
                            confirm: {
                                label:'Import',
                            }
                        }
                    });
                }
            }).fail(function(xhr, textStatus, error) {
                self.messageClass('text-danger');
                self.node_message('Could not GET S3 accounts for user.');
            });
};

/** Reset all fields from S3 credentials input modal */
ViewModel.prototype.clearModal = function() {
    var self = this;
    self.message('');
    self.messageClass('text-info');
    self.secretKey(null);
    self.accessKey(null);
};

ViewModel.prototype.sendAuth = function() {
    var self = this;
    if( !self.accessKey() && !self.secretKey() ){
        self.changeMessage('Please enter both an API access key and secret key.', 'text-danger');
        return;
    }

    if (!self.accessKey() ){
        self.changeMessage('Please enter an API access key.', 'text-danger');
        return;
    }

    if (!self.secretKey() ){
        self.changeMessage('Please enter an API secret key.', 'text-danger');
        return;
    }
    self.creatingCredentials(true);
        
    return $osf.postJSON(
        self.urls().create, {
            secret_key: self.secretKey(),
            access_key: self.accessKey()
        }
    ).done(function(response) {
        self.clearModal();
        $modal.modal('hide');
        self.creatingCredentials(false);
        self.changeMessage('Successfully added S3 credentials.', 'text-success', null, true);
        self.updateFromData(response);
        self.importAuth();
    }).fail(function(xhr, status, error) {
        self.creatingCredentials(false);
        var message = '';
        var response = JSON.parse(xhr.responseText);
        if (response && response.message) {
            message = response.message;
        }
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not add S3 credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.createBucket = function(bucketName, bucketLocation) {
    var self = this;
    self.creating(true);
    bucketName = bucketName.toLowerCase();
    return $osf.postJSON(
        self.urls().create_bucket, {
            bucket_name: bucketName,
            bucket_location: bucketLocation
        }
    ).done(function(response) {
        self.creating(false);
        self.bucketList(response.buckets);
        self.loadedBucketList(true);
        self.selectedBucket(bucketName);
        self.showSelect(true);
        var msg = 'Successfully created bucket "' + bucketName + '". You can now select it from the drop down list.';
        var msgType = 'text-success';
        self.changeMessage(msg, msgType, null, true);
    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating bucket';
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: $osf.htmlEscape(title),
            message: $osf.htmlEscape(message),
            callback: function(result) {
                if (result) {
                    self.openCreateBucket();
                }
            },
            buttons:{
                confirm:{
                    label:'Try again'
                }
            }
        });
    });
};

ViewModel.prototype.openCreateBucket = function() {
    var self = this;

    // Generates html options for key-value pairs in BUCKET_LOCATION_MAP
    function generateBucketOptions(locations) {
        var options = '';
        for (var location in locations) {
            if (self.settings.bucketLocations.hasOwnProperty(location)) {
                options = options + ['<option value="', location, '">', $osf.htmlEscape(locations[location]), '</option>', '\n'].join('');
            }
        }
        return options;
    }

    bootbox.dialog({
        title: 'Create a new bucket',
        message:
                '<div class="row"> ' +
                    '<div class="col-md-12"> ' +
                        '<form class="form-horizontal" onsubmit="return false"> ' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketName">Bucket Name</label> ' +
                                '<div class="col-md-8"> ' +
                                    '<input id="bucketName" name="bucketName" type="text" placeholder="Enter bucket name" class="form-control" autofocus> ' +
                                    '<div>' +
                                        '<span id="bucketModalErrorMessage" ></span>' +
                                    '</div>'+
                                '</div>' +
                            '</div>' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketLocation">Bucket Location</label> ' +
                                '<div class="col-md-8"> ' +
                                    '<select id="bucketLocation" name="bucketLocation" class="form-control"> ' +
                                        generateBucketOptions(self.settings.bucketLocations) +
                                    '</select>' +
                                '</div>' +
                            '</div>' +
                        '</form>' +
                    '</div>' +
                '</div>',
        buttons: {
            cancel: {
                label: 'Cancel',
                className: 'btn-default'
            },
            confirm: {
                label: 'Create',
                className: 'btn-success',
                callback: function () {
                    var bucketName = $('#bucketName').val();
                    var bucketLocation = $('#bucketLocation').val();

                    if (!bucketName) {
                        var errorMessage = $('#bucketModalErrorMessage');
                        errorMessage.text('Bucket name cannot be empty');
                        errorMessage[0].classList.add('text-danger');
                        return false;
                    } else if (!isValidBucketName(bucketName, false)) {
                        bootbox.confirm({
                            title: 'Invalid bucket name',
                            message: 'Amazon S3 buckets can contain lowercase letters, numbers, and hyphens separated by' +
                            ' periods.  Please try another name.',
                            callback: function (result) {
                                if (result) {
                                    self.openCreateBucket();
                                }
                            },
                            buttons: {
                                confirm: {
                                    label: 'Try again'
                                }
                            }
                        });
                    } else {
                        self.createBucket(bucketName, bucketLocation);
                    }
                }
            }
        }
    });
};

ViewModel.prototype.fetchBucketList = function() {
    var self = this;

    var ret = $.Deferred();
    if(self.loadedBucketList()){
        ret.resolve(self.bucketList());
    }
    else{
         $.ajax({
            url: self.urls().bucket_list,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.loadedBucketList(true);
            ret.resolve(response.buckets);
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of S3 buckets at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-danger', null, null);
            Raven.captureMessage('Could not GET s3 bucket list', {
                url: self.urls().bucketList,
                textStatus: status,
                error: error
            });
            ret.reject(xhr, status, error);
        });
    }
    return ret.promise();
};

ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    var ret = $.Deferred();
    var applySettings = function(settings){
        self.nodeHasAuth(settings.nodeHasAuth);
        self.userHasAuth(settings.userHasAuth);
        self.userIsOwner(settings.userIsOwner);
        self.ownerName(settings.ownerName);
        self.validCredentials(settings.validCredentials);
        self.currentBucket(settings.hasBucket ? settings.bucket : null);
        if (settings.urls) {
            self.urls(settings.urls);
        }
        if (self.nodeHasAuth() && !self.validCredentials()) {
            var message = '';
            if(self.userIsOwner()) {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing S3 on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            }
            else {
                message = 'Could not retrieve S3 settings at ' +
                    'this time. The S3 addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.';
            }
            self.changeMessage(message, 'text-danger', null, true);
        }
        ret.resolve(settings);
    };
    if ((typeof data === 'undefined') || (data === null) ){
        return self.fetchFromServer()
            .done(applySettings);
    }
    else {
        applySettings(data);
    }
    return ret.promise();
};

ViewModel.prototype.fetchFromServer = function() {
    var self = this;
    var ret = $.Deferred();
    $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json',
        contentType: 'application/json'
    })
    .done(function(response) {
        var settings = response.result;
        self.loadedSettings(true);
        ret.resolve(settings);
    })
    .fail(function(xhr, status, error) {
        var message = 'Could not retrieve S3 settings at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger', null, true);
        Raven.captureMessage('Could not GET s3 settings', {
            url: self.url,
            textStatus: status,
            error: error
        });
        ret.reject(xhr, status, error);
    });
    return ret.promise();
};

/** Change the flashed message. */
ViewModel.prototype.changeMessage = function(text, css, timeout, node) {
    var self = this;
    if (node) {
        self.node_message(text);
    } else {
        self.message(text);
    }
    var cssClass = css || 'text-info';
    self.messageClass(cssClass);
    if (timeout) {
        // Reset message after timeout period
        setTimeout(function() {
            self.message('');
            self.node_message('');
            self.messageClass('text-info');
        }, timeout);
    }
};

var S3Config = function(selector, settings) {
    var viewModel = new ViewModel(selector, settings);
    $osf.applyBindings(viewModel, selector);
    viewModel.updateFromData();
};

module.exports = {
    S3NodeConfig: S3Config,
    _S3NodeConfigViewModel: ViewModel,
    _isValidBucketName: isValidBucketName
};
