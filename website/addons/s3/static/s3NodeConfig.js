'use strict';
var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

ko.punches.enableAll();

var ViewModel = function(url, selector) {
    var self = this;

    self.url = url;
    self.selector = selector;

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

    self.accessKey = ko.observable('');
    self.secretKey = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);
    self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
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

ViewModel.prototype.selectBucket = function() {
    var self = this;
    self.loading(true);
    return $osf.postJSON(
            self.urls().set_bucket, {
                's3_bucket': self.selectedBucket()
            }
        )
        .done(function(response) {
            self.updateFromData(response);
            self.changeMessage('Successfully linked S3 bucket "' + self.currentBucket() + '". Go to the <a href="' +
                               self.urls().files + '">Files page</a> to view your content.', 'text-success');
            self.loading(false);
        })
        .fail(function(xhr, status, error) {
            self.loading(false);
            var message = 'Could not change S3 bucket at this time. ' +
                'Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not set S3 bucket', {
                url: self.urls().setBucket,
                textStatus: status,
                error: error
            });
        });
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
    }).fail(function(xhr, status, error) {
        var message = 'Could not deauthorize S3 at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
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
        title: 'Deauthorize S3?',
        message: 'Are you sure you want to remove this S3 authorization?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        }
    });
};

ViewModel.prototype._importAuthConfirm = function() {
    var self = this;
    return $osf.postJSON(
        self.urls().import_auth, {}
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

};

ViewModel.prototype.importAuth = function() {
    var self = this;
    bootbox.confirm({
        title: 'Import S3 credentials?',
        message: 'Are you sure you want to authorize this project with your S3 credentials?',
        callback: function(confirmed) {
            if (confirmed) {
                return self._importAuthConfirm();
            }
        }
    });
};

ViewModel.prototype.createCredentials = function() {
    var self = this;
    self.creatingCredentials(true);
    return $osf.postJSON(
        self.urls().create_auth, {
            secret_key: self.secretKey(),
            access_key: self.accessKey()
        }
    ).done(function(response) {
        self.creatingCredentials(false);
        self.changeMessage('Successfully added S3 credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        self.creatingCredentials(false);
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
        self.changeMessage(msg, msgType);
    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating bucket';
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: title,
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateBucket();
                }
            }
        });
    });
};

ViewModel.prototype.openCreateBucket = function() {
    var self = this;

    var isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

    bootbox.dialog({
        title: 'Create a new bucket',
        message:
                '<div class="row"> ' +
                    '<div class="col-md-12"> ' +
                        '<form class="form-horizontal"> ' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketName">Bucket Name</label> ' +
                                '<div class="col-md-4"> ' +
                                    '<input id="bucketName" name="bucketName" type="text" placeholder="Enter bucket\'s name" class="form-control" autofocus> ' +
                                '</div>' +
                            '</div>' +
                            '<div class="form-group"> ' +
                                '<label class="col-md-4 control-label" for="bucketLocation">Bucket Location</label> ' +
                                '<div class="col-md-4"> ' +
                                    '<select id="bucketLocation" name="bucketLocation" class="form-control"> ' +
                                        '<option value="' + window.contextVars.s3Settings.defaultBucketLocationValue + '' +
                                            '" selected>' + window.contextVars.s3Settings.defaultBucketLocationMessage + '</option> ' +
                                        '<option value="EU">Europe Standard</option> ' +
                                        '<option value="us-west-1">California</option> ' +
                                        '<option value="us-west-2">Oregon</option> ' +
                                        '<option value="ap-northeast-1">Tokyo</option> ' +
                                        '<option value="ap-southeast-1">Singapore</option> ' +
                                        '<option value="ap-southeast-2">Sydney, Australia</option> ' +
                                        '<option value="cn-north-1">Beijing, China</option> ' +
                                    '</select>' +
                                '</div>' +
                            '</div>' +
                        '</form>' +
                    '</div>' +
                '</div>',
        buttons: {
            confirm: {
                label: 'Save',
                className: 'btn-success',
                callback: function () {
                    var bucketName = $('#bucketName').val();
                    var bucketLocation = $('#bucketLocation').val();

                    if (!bucketName) {
                        return;
                    } else if (isValidBucket.exec(bucketName) == null) {
                        bootbox.confirm({
                            title: 'Invalid bucket name',
                            message: 'Sorry, that\'s not a valid bucket name. Try another name?',
                            callback: function(result) {
                                if (result) {
                                    self.openCreateBucket();
                                }
                            }
                        });
                    } else {
                        self.createBucket(bucketName, bucketLocation);
                    }
                }
            },
            cancel: {
                label: 'Cancel',
                className: 'btn-default'
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
            self.changeMessage(message, 'text-warning');
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
        self.nodeHasAuth(settings.node_has_auth);
        self.userHasAuth(settings.user_has_auth);
        self.userIsOwner(settings.user_is_owner);
        self.ownerName(settings.owner);
        self.validCredentials(settings.valid_credentials);
        self.currentBucket(settings.has_bucket ? settings.bucket : null);
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
            self.changeMessage(message, 'text-danger');
        }
        ret.resolve(settings);
    };
    if (typeof data === 'undefined'){
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
        self.changeMessage(message, 'text-warning');
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
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
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

var S3Config = function(selector, url) {
    var viewModel = new ViewModel(url, selector);
    $osf.applyBindings(viewModel, selector);
    viewModel.updateFromData();
};

module.exports = {
    S3NodeConfig: S3Config,
    _S3NodeConfigViewModel: ViewModel
};
