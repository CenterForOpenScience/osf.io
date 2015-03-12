'use strict';

var ko = require('knockout');
require('knockout-punches');
require('knockout-mapping');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

ko.punches.enableAll();

var noop = function(){};

var ViewModel = function(url, selector) {
    var self = this;

    self.url = url;
    self.selector = selector;

    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.ownerName = ko.observable('');

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
        return self.nodeHasAuth();
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
        return !self.nodeHasAuth() && !self.userHasAuth();
    });
    self.canChange = ko.pureComputed(function() {
        return self.userIsOwner() && self.nodeHasAuth();
    });
    self.allowSelectBucket = ko.pureComputed(function() {
        return (self.bucketList().length > 0 || self.loadedBucketList()) && (!self.loading());
    });
};

ViewModel.prototype.toggleSelect = function() {
    this.showSelect(!this.showSelect());
    if (!this.loadedBucketList()) {
        return this.fetchBucketList();
    }
};

ViewModel.prototype.selectBucket = function() {
    var self = this;
    self.loading(true);
    return $osf.postJSON(
            self.urls().setBucket, {
                's3_bucket': self.selectedBucket()
            }
        )
        .done(function(response) {
            self.updateFromData(response);
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            self.changeMessage('Successfully linked S3 bucket \'' + self.currentBucket() + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.', 'text-success');
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

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;

    bootbox.confirm({
        title: 'Deauthorize S3?',
        message: 'Are you sure you want to remove this S3 authorization?',
        callback: function(confirm) {
            if (confirm) {
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
            }
        }
    });
};

ViewModel.prototype.importAuth = function() {
    var self = this;
    var onImportConfirm = function() {
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
    };

    bootbox.confirm({
        title: 'Import S3 credentials?',
        message: 'Are you sure you want to authorize this project with your S3 credentials?',
        callback: function(confirmed) {
            if (confirmed) {
                return onImportConfirm();
            }
        }
    });
};

ViewModel.prototype.createCredentials = function() {
    var self = this;
    return $osf.postJSON(
        self.urls().createAuth, {
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

ViewModel.prototype.createBucket = function(bucketName) {
    var self = this;
    self.creating(true);
    bucketName = bucketName.toLowerCase();
    return $osf.postJSON(
        self.urls().createBucket, {
            bucket_name: bucketName
        }
    ).done(function(response) {
        self.creating(false);
        self.updateFromData(response);
        self.changeMessage('Successfully created bucket \'' + bucketName + '\'. You can now select it from the drop down list.', 'text-success');
        self.bucketList().push(bucketName);
        if (!self.loadedBucketList()) {
            self.fetchBucketList();
        }
        self.selectedBucket(bucketName);
        self.selectedBucket();
        self.bucketList();
        self.showSelect(true);
    }).fail(function(xhr) {
        var message = JSON.parse(xhr.responseText).message;
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: 'Duplicate bucket name',
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

    bootbox.prompt('Name your new bucket', function(bucketName) {
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
            self.createBucket(bucketName);
        }
    });
};

ViewModel.prototype.fetchBucketList = function() {
    var self = this;
    return $.ajax({
            url: self.urls().bucketList,
            type: 'GET',
            dataType: 'json'
        })
        .done(function(response) {
            self.bucketList(response.buckets);
            self.loadedBucketList(true);
            self.selectedBucket(self.currentBucket());
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of S3 buckets at' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not GET s3 bucket list', {
                url: self.urls().bucketList,
                textStatus: status,
                error: error
            });
        });
};

ViewModel.prototype.updateFromData = function(settings) {
    var self = this;
    self.nodeHasAuth(settings.node_has_auth);
    self.userHasAuth(settings.user_has_auth);
    self.userIsOwner(settings.user_is_owner);
    self.ownerName(settings.owner);
    self.currentBucket(settings.has_bucket ? settings.bucket : 'None');
    self.loadedSettings(true);
    if (settings.urls) {
        self.urls(settings.urls);
    }
};

ViewModel.prototype.fetchFromServer = function(callback) {
    var self = this;
    return $.ajax({
        url: self.url,
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            var settings = response.result;
            self.updateFromData(settings);
        },
        error: function(xhr, status, error){
            var message = 'Could not retrieve S3 settings at ' +
                    'this time. Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not GET s3 settings', {
                url: self.url,
                textStatus: status,
                error: error
            });
        }
    })
        .done(callback || noop);
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
    viewModel.fetchFromServer();
};

module.exports = {
    S3NodeConfig: S3Config,
    _S3NodeConfigViewModel: ViewModel
};
