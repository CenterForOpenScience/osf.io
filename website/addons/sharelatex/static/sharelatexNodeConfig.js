'use strict';
var ko = require('knockout');
require('knockout.punches');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var sharelatexSettings = require('json!./settings.json');

ko.punches.enableAll();

var defaultSettings = {
    url: ''
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
    self.projectList = ko.observableArray([]);
    self.loadedBucketList = ko.observable(false);
    self.currentBucket = ko.observable('');
    self.selectedBucket = ko.observable('');

    self.authToken = ko.observable('');
    self.sharelatexUrl = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);
    self.creatingCredentials = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

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
        return (self.projectList().length > 0 || self.loadedBucketList()) && (!self.loading());
    });

    self.saveButtonText = ko.pureComputed (function(){
        return self.loading()? 'Saving': 'Save';
    });
};

ViewModel.prototype.updateBucketList = function(){
    var self = this;
    return self.fetchProjectList()
        .done(function(projects){
            self.projectList(projects);
            self.selectedBucket(self.currentBucket());
        });
};

var isValidBucketName = function(projectName, allowPeriods) {
    var isValidBucket;

    if (allowPeriods === true) {
        isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;
    } else {isValidBucket = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d-]{2,61}[^.]$/;}

    return isValidBucket.test(projectName);
};

ViewModel.prototype.selectBucket = function() {
    var self = this;

    self.loading(true);

    var ret = $.Deferred();
    if (!isValidBucketName(self.selectedBucket(), false)) {
        self.loading(false);
        bootbox.alert({
            title: 'Invalid project name',
            message: 'Sorry, the ShareLatex addon only supports project names without periods.'
        });
        ret.reject();
    } else {
        $osf.postJSON(
                self.urls().set_project, {
                    'sharelatex_project': self.selectedBucket()
                    }
                )
            .done(function (response) {
                var projectName = $("#sharelatex_project option[value='" + self.selectedBucket() + "']").text();
                self.updateFromData(response);
                self.changeMessage('Successfully linked ShareLatex project "' + projectName + '". Go to the <a href="' +
                    self.urls().files + '">Files page</a> to view your content.', 'text-success');
                self.loading(false);
                ret.resolve(response);
            })
            .fail(function (xhr, status, error) {
                self.loading(false);
                var message = 'Could not change ShareLatex project at this time. ' +
                    'Please refresh the page. If the problem persists, email ' +
                    '<a href="mailto:support@osf.io">support@osf.io</a>.';
                self.changeMessage(message, 'text-danger');
                Raven.captureMessage('Could not set ShareLatex project', {
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
        self.changeMessage('Disconnected ShareLatex.', 'text-warning', 3000);
    }).fail(function(xhr, status, error) {
        var message = 'Could not disconnect ShareLatex at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not remove ShareLatex authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disconnect ShareLatex Account?',
        message: 'Are you sure you want to remove this ShareLatex account?',
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
    return $osf.postJSON(
        self.urls().import_auth, {}
    ).done(function(response) {
        self.changeMessage('Successfully imported ShareLatex credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        var message = 'Could not import ShareLatex credentials at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not import ShareLatex credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });

};

ViewModel.prototype.importAuth = function() {
    var self = this;
    bootbox.confirm({
        title: 'Import ShareLatex credentials?',
        message: 'Are you sure you want to authorize this project with your ShareLatex credentials?',
        callback: function(confirmed) {
            if (confirmed) {
                return self._importAuthConfirm();
            }
        },
        buttons:{
            confirm:{
                label:'Import'
            }
        }
    });
};

ViewModel.prototype.createCredentials = function() {
    var self = this;
    self.creatingCredentials(true);

    return $osf.postJSON(
        self.urls().create_auth, {
            auth_token: self.authToken(),
            sharelatex_url: self.sharelatexUrl()
        }
    ).done(function(response) {
        self.creatingCredentials(false);
        self.changeMessage('Successfully added ShareLatex credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error) {
        self.creatingCredentials(false);
        var message = '';
        var response = JSON.parse(xhr.responseText);
        if (response && response.message) {
            message = response.message;
        }
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not add ShareLatex credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.fetchProjectList = function() {
    var self = this;

    var ret = $.Deferred();
    if (self.loadedBucketList()) {
        ret.resolve(self.projectList());
    } else {
         console.log(self.urls().project_list);
         $.ajax({
            url: self.urls().project_list,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.loadedBucketList(true);
            ret.resolve(response);
        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of ShareLatex projects at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-danger');
            Raven.captureMessage('Could not GET sharelatex project list', {
                url: self.urls().projectList,
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
        self.currentBucket(settings.has_project ? settings.project : null);
        if (settings.urls) {
            self.urls(settings.urls);
        }
        if (self.nodeHasAuth() && !self.validCredentials()) {
            var message = '';
            if(self.userIsOwner()) {
                message = 'Could not retrieve ShareLatex settings at ' +
                    'this time. The ShareLatex credentials may no longer be valid.' +
                    ' Try deauthorizing and reauthorizing ShareLatex on your <a href="' +
                    self.urls().settings + '">account settings page</a>.';
            }
            else {
                message = 'Could not retrieve ShareLatex settings at ' +
                    'this time. The ShareLatex addon credentials may no longer be valid.' +
                    ' Contact ' + self.ownerName() + ' to verify.';
            }
            self.changeMessage(message, 'text-danger');
        }
        self.updateBucketList();
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
        var message = 'Could not retrieve ShareLatex settings at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-danger');
        Raven.captureMessage('Could not GET sharelatex settings', {
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

var ShareLatexConfig = function(selector, settings) {
    var viewModel = new ViewModel(selector, settings);
    $osf.applyBindings(viewModel, selector);
    viewModel.updateFromData();
};

module.exports = {
    ShareLatexNodeConfig: ShareLatexConfig,
    _ShareLatexNodeConfigViewModel: ViewModel,
    _isValidBucketName: isValidBucketName
};
