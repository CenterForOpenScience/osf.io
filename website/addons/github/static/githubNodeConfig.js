'use strict';

var ko = require('knockout');
require('knockout.punches');
require('knockout-mapping');
var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

ko.punches.enableAll();

var noop = function() {};

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
    self.repoList = ko.observableArray([]);
    self.loadedRepoList = ko.observable(false);
    self.currentRepo = ko.observable('');
    self.selectedRepo = ko.observable('');

    self.accessToken = ko.observable('');

    self.loading = ko.observable(false);
    self.creating = ko.observable(false);

    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    self.showSelect = ko.observable(false);

    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth();
    });
    self.disableSettings = ko.pureComputed(function() {
        return !(self.userHasAuth() && self.userIsOwner());
    });
    self.showNewRepo = ko.pureComputed(function() {
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
    self.allowSelectRepo = ko.pureComputed(function() {
        return (self.repoList().length > 0 || self.loadedRepoList()) && (!self.loading());
    });

};

ViewModel.prototype.toggleSelect = function() {
    var self = this;
    self.showSelect(!self.showSelect());
    return self.fetchRepoList()
    .done(function(repos){
            debugger;
        self.repoList(repos);
        self.selectedRepo(self.currentRepo());
    });
};

ViewModel.prototype.selectRepo = function() {
    var self = this;
    self.loading(true);
    return $osf.postJSON(
            self.urls().set_repo, {
                'github_repo': self.selectedRepo()
            }
        )
        .done(function(response) {
            self.updateFromData(response);
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            self.changeMessage('Successfully linked Github repo \'' + self.currentRepo() + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.', 'text-success');
            self.loading(false);
            self.showSelect(false);
        })
        .fail(function(xhr, status, error) {
            self.loading(false);
            var message = 'Could not change Github repo at this time. ' +
                'Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not set Github repo', {
                url: self.urls().set_repo,
                textStatus: status,
                error: error
            });
        });
};

ViewModel.prototype.createNodeAuth = function() {
    var self = this;
    window.location.href = self.urls().create_auth;
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
        var message = 'Could not deauthorize Github at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not remove Github authorization.', {
            url: self.urls().deauthorize,
            textStatus: status,
            error: error
        });
    });
};

ViewModel.prototype.deauthorizeNode = function() {
    var self = this;
    bootbox.confirm({
        title: 'Deauthorize Github?',
        message: 'Are you sure you want to remove this Github authorization?',
        callback: function(confirm) {
            if (confirm) {
                self._deauthorizeNodeConfirm();
            }
        }
    });
};

ViewModel.prototype._importAuthConfirm = function() {

    return $osf.postJSON(
        self.urls().import_auth, {}
    ).done(function(response) {
        self.changeMessage('Successfully imported Github credentials.', 'text-success');
        self.updateFromData(response);

    }).fail(function(xhr, status, error) {
        var message = 'Could not import Github credentials at ' +
            'this time. Please refresh the page. If the problem persists, email ' +
            '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not import Github credentials', {
            url: self.urls().import_auth,
            textStatus: status,
            error: error
        });
    });

};

ViewModel.prototype.importAuth = function() {
    var self = this;
    bootbox.confirm({
        title: 'Import Github credentials?',
        message: 'Are you sure you want to authorize this project with your Github credentials?',
        callback: function(confirmed) {
            if (confirmed) {
                return self._importAuthConfirm();
            }
        }
    });
};




ViewModel.prototype.createRepo = function(repoName) {
    var self = this;
    self.creating(true);
    return $osf.postJSON(
        self.urls().create_repo, {
            repo_name: repoName
        }
    ).done(function(response) {
        repoName = response.github_user + ' / ' + response.repo;
        self.creating(false);
        self.updateFromData(response);
        self.changeMessage('Successfully created repo \'' + repoName + '\'. You can now select it from the drop down list.', 'text-success');
        return self.fetchRepoList()
            .done(function(repos){
            self.repoList(repos);
            self.selectedRepo(repoName);
            self.showSelect(true);
            });

    }).fail(function(xhr) {
        var resp = JSON.parse(xhr.responseText);
        var message = resp.message;
        var title = resp.title || 'Problem creating repo';
        self.creating(false);
        if (!message) {
            message = 'Looks like that name is taken. Try another name?';
        }
        bootbox.confirm({
            title: title,
            message: message,
            callback: function(result) {
                if (result) {
                    self.openCreateRepo();
                }
            }
        });
    });
};

ViewModel.prototype.openCreateRepo = function() {
    var self = this;

    var isValidRepo = /^(?!.*(\.\.|-\.))[^.][a-z0-9\d.-]{2,61}[^.]$/;

    bootbox.prompt('Name your new repo', function(repoName) {
        if (!repoName) {
            return;
        } else if (isValidRepo.exec(repoName) == null) {
            bootbox.confirm({
                title: 'Invalid repo name',
                message: 'Sorry, that\'s not a valid repo name. Try another name?',
                callback: function(result) {
                    if (result) {
                        self.openCreateRepo();
                    }
                }
            });
        } else {
            self.createRepo(repoName);
        }
    });
};


ViewModel.prototype.fetchRepoList = function() {
    var self = this;

    var ret = $.Deferred();
    if(self.loadedRepoList()){
        ret.resolve(self.repoList());
    }
    else{
         $.ajax({
            url: self.urls().repo_list,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            self.loadedRepoList(true);
            ret.resolve(response.repo_names);


        })
        .fail(function(xhr, status, error) {
            var message = 'Could not retrieve list of Github repos at' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
            self.changeMessage(message, 'text-warning');
            Raven.captureMessage('Could not GET github repo list', {
                url: self.urls().repo_list,
                textStatus: status,
                error: error
            });
            ret.reject(xhr, status, error);
        });
    }
    return ret.promise();
};

ViewModel.prototype.updateFromData = function(settings){
    var self = this;
    self.nodeHasAuth(settings.node_has_auth);
    self.userHasAuth(settings.user_has_auth);
    self.userIsOwner(settings.user_is_owner);
    self.ownerName(settings.owner);
    self.currentRepo(settings.has_repo ? settings.repo : 'None');
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
            error: function(xhr, status, error) {
                var message = 'Could not retrieve Github settings at ' +
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


ViewModel.prototype.createCredentials = function() {
    var self = this;
    $osf.postJSON(
        self.urls().create_auth,
        {
            secret_key: self.secretKey(),
            access_key: self.accessKey()
        }
    ).done(function(response) {
        self.creatingCredentials(false);
        self.changeMessage('Successfully added Github credentials.', 'text-success');
        self.updateFromData(response);
    }).fail(function(xhr, status, error){
        self.creatingCredentials(false);
        var message = 'Could not add Github credentials at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        self.changeMessage(message, 'text-warning');
        Raven.captureMessage('Could not add Github credentials', {
            url: self.urls().importAuth,
            textStatus: status,
            error: error
        });
    });
};



var githubConfig = function(selector, url){
    var viewModel = new ViewModel(url, selector);
    $osf.applyBindings(viewModel, selector);
    viewModel.fetchFromServer();
};

module.exports = {
    githubNodeConfig: githubConfig,
    _githubNodeConfigViewModel: ViewModel
};